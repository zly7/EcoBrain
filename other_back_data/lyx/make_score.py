# -*- coding: utf-8 -*-
"""
逐行产业细分类能源需求打分（1-5整数）
- 输入：csv 或 xlsx（包含 12 列：大类/中类/小类/细分类 的 code + 日文 + 中文）
- 输出：新增 8 列的打分 csv
- 日志：逐行保存模型原始输出 + 解析后的分数 + 简要依据 到 jsonl

注意：
1) API_KEY 必须在本文件顶部手动填写（按你的要求不使用环境变量）
2) 这里的“推理过程”采用“可审计的简要依据 + 原始输出”，不会请求或保存隐藏思维链
"""

import json
import os
import re
import time
from typing import Any, Dict, Optional, Tuple

import pandas as pd
from openai import OpenAI


# =========================
# ✅ 0) 直接在这里改参数即可
# =========================
API_KEY = ""  # <<< 在这里填入你的 API Key（不要留空）
BASE_URL = "https://api.xiaomimimo.com/v1"
MODEL = "mimo-v2-flash"

# 输入文件（csv/xlsx）
INPUT_PATH = "/mnt/data/未打分.xlsx"

# 输出打分后的 CSV（utf-8-sig，Excel 友好）
OUTPUT_CSV_PATH = "/mnt/data/已打分.csv"

# 逐行日志（jsonl）
LOG_JSONL_PATH = "/mnt/data/推理过程.jsonl"

# 行范围控制（断点/分批跑用）
START_ROW = 0
END_ROW_EXCLUSIVE = None  # None 表示到最后；或写成比如 1000

# 每次调用后 sleep（避免限流）
SLEEP_SECONDS = 0.0

# 每处理多少行就把 CSV 落盘一次（防中断丢进度）
FLUSH_EVERY_N_ROWS = 10

# 失败重试次数
MAX_RETRIES = 4


# =========================
# 输出列定义（8维度）
# =========================
SCORE_COLUMNS = [
    "高品位热能",
    "中品位热能",
    "低品位热能",
    "高品位冷能",
    "中品位冷能",
    "低品位冷能",
    "电能",
    "天然气",
]

# JSON key -> 中文列名（稳定解析用）
JSON_KEYS = {
    "high_grade_heat": "高品位热能",
    "medium_grade_heat": "中品位热能",
    "low_grade_heat": "低品位热能",
    "high_grade_cold": "高品位冷能",
    "medium_grade_cold": "中品位冷能",
    "low_grade_cold": "低品位冷能",
    "electricity": "电能",
    "natural_gas": "天然气",
}

REQUIRED_INPUT_COLUMNS = [
    "大类代码", "大类（日文）", "大类（中文）",
    "中类代码", "中类（日文）", "中类（中文）",
    "小类代码", "小类（日文）", "小类（中文）",
    "细分类代码", "细分类（日文）", "细分类（中文）",
]


def load_table(path: str) -> pd.DataFrame:
    ext = os.path.splitext(path)[1].lower()
    if ext in [".xlsx", ".xls"]:
        df = pd.read_excel(path, header=0)
    elif ext in [".csv"]:
        # 兼容常见编码：utf-8-sig / cp932 / gbk
        try:
            df = pd.read_csv(path, encoding="utf-8-sig")
        except UnicodeDecodeError:
            try:
                df = pd.read_csv(path, encoding="cp932")
            except UnicodeDecodeError:
                df = pd.read_csv(path, encoding="gbk")
    else:
        raise ValueError(f"不支持的输入格式: {ext}，请用 .csv 或 .xlsx")

    # 列名满足则直接返回
    if set(REQUIRED_INPUT_COLUMNS).issubset(set(df.columns)):
        return df

    # 容错：把第一行当header再试一次
    if ext in [".xlsx", ".xls"]:
        df2 = pd.read_excel(path, header=None)
    else:
        df2 = pd.read_csv(path, header=None)

    first_row = df2.iloc[0].tolist()
    if len(first_row) >= 12:
        df2 = df2.iloc[1:].copy()
        df2.columns = first_row[: len(df2.columns)]
        if set(REQUIRED_INPUT_COLUMNS).issubset(set(df2.columns)):
            return df2

    raise ValueError(
        "输入文件列名不符合预期。需要包含这12列：\n"
        + "\n".join(REQUIRED_INPUT_COLUMNS)
        + f"\n实际列名：{list(df.columns)}"
    )


def build_messages(row: Dict[str, Any]) -> list:
    """
    给单行构造 prompt，要求模型只输出 JSON（便于解析）。
    “rationale”要求为可读的简要依据（<=200字），作为可审计记录。
    """
    industry_desc = {
        "大类": {"代码": row.get("大类代码"), "日文": row.get("大类（日文）"), "中文": row.get("大类（中文）")},
        "中类": {"代码": row.get("中类代码"), "日文": row.get("中类（日文）"), "中文": row.get("中类（中文）")},
        "小类": {"代码": row.get("小类代码"), "日文": row.get("小类（日文）"), "中文": row.get("小类（中文）")},
        "细分类": {"代码": row.get("细分类代码"), "日文": row.get("细分类（日文）"), "中文": row.get("细分类（中文）")},
    }

    system = (
        "你是一个“能源需求评估”助手。你将针对一个产业细分类，在现实生活中典型生产/运营场景下，"
        "对8种能源需求强度进行打分（1-5整数）。\n"
        "评分规则：1=需求最低，5=需求最高。\n"
        "维度解释（用于一致性，不必逐字复述）：\n"
        "- 高品位热能：高温工艺热/高温蒸汽/熔融、热处理等（常见>~400℃）\n"
        "- 中品位热能：中温工艺热/蒸汽/烘干等（约150~400℃）\n"
        "- 低品位热能：热水/低温加热/保温/清洗等（<~150℃）\n"
        "- 高品位冷能：深冷/低温冷冻（例如<-20℃ 或更低，视行业）\n"
        "- 中品位冷能：冷冻/冷藏（例如-20~0℃）\n"
        "- 低品位冷能：空调/冷却水/常温冷却（例如0~20℃）\n"
        "- 电能：电力驱动（电机、压缩机、照明、控制系统等）\n"
        "- 天然气：以天然气作为燃料/原料气的需求强度\n\n"
        "输出必须严格为JSON对象（不要markdown、不要多余文字），字段如下：\n"
        "{\n"
        '  "high_grade_heat": 1-5,\n'
        '  "medium_grade_heat": 1-5,\n'
        '  "low_grade_heat": 1-5,\n'
        '  "high_grade_cold": 1-5,\n'
        '  "medium_grade_cold": 1-5,\n'
        '  "low_grade_cold": 1-5,\n'
        '  "electricity": 1-5,\n'
        '  "natural_gas": 1-5,\n'
        '  "rationale": "用中文给出不超过200字的简要依据，概括主要用能环节"\n'
        "}\n"
    )

    user = (
        "请对以下产业细分类进行8维度能源需求打分（1-5整数），并按要求只输出JSON：\n"
        f"{json.dumps(industry_desc, ensure_ascii=False)}"
    )

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def extract_json(text: str) -> Dict[str, Any]:
    """从模型输出中提取JSON对象（要求纯JSON，但做容错）。"""
    text = (text or "").strip()

    # 直接解析
    try:
        return json.loads(text)
    except Exception:
        pass

    # 截取第一个 { ... } 块
    m = re.search(r"\{.*\}", text, flags=re.S)
    if not m:
        raise ValueError("未找到JSON对象")
    candidate = m.group(0).strip()

    # 再解析一次
    try:
        return json.loads(candidate)
    except Exception:
        # 容错：把单引号替换为双引号（可能误伤，但在输出不规范时能救回来）
        candidate2 = candidate.replace("'", '"')
        return json.loads(candidate2)


def validate_and_map_scores(obj: Dict[str, Any]) -> Tuple[Dict[str, int], str]:
    """校验字段齐全、分数范围，并映射为中文列名->分数。"""
    scores_cn: Dict[str, int] = {}
    for k, cn_col in JSON_KEYS.items():
        if k not in obj:
            raise ValueError(f"缺少字段: {k}")
        v = obj[k]
        if isinstance(v, str) and v.isdigit():
            v = int(v)
        if not isinstance(v, int):
            raise ValueError(f"字段{k}不是整数: {v}")
        if v < 1 or v > 5:
            raise ValueError(f"字段{k}超出范围1-5: {v}")
        scores_cn[cn_col] = v

    rationale = obj.get("rationale", "")
    if rationale is None:
        rationale = ""
    rationale = str(rationale).strip()
    return scores_cn, rationale


def append_jsonl(path: str, record: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def call_llm(client: OpenAI, messages: list) -> str:
    """调用模型，带指数退避重试。"""
    last_err: Optional[Exception] = None
    for attempt in range(MAX_RETRIES):
        try:
            completion = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                max_completion_tokens=512,
                temperature=0.2,
                top_p=0.9,
                stream=False,
                frequency_penalty=0,
                presence_penalty=0,
                extra_body={"thinking": {"type": "disabled"}},  # 与你示例保持一致
            )
            return completion.choices[0].message.content or ""
        except Exception as e:
            last_err = e
            time.sleep(min(2 ** attempt, 16))
    raise RuntimeError(f"多次重试仍失败: {last_err}")


def main():
    # 1) 参数检查
    if not API_KEY:
        raise ValueError('API_KEY 为空：请在脚本顶部把 API_KEY = "..." 填上（按要求不依赖环境变量）。')

    # 2) 读取数据
    df = load_table(INPUT_PATH).copy()

    # 3) 初始化输出列
    for col in SCORE_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA

    # 可选：把“简要依据”也写到CSV里（你也可以删掉这一列）
    if "打分依据" not in df.columns:
        df["打分依据"] = pd.NA

    # 4) 初始化 OpenAI client
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

    n = len(df)
    start = max(0, START_ROW)
    end = END_ROW_EXCLUSIVE if END_ROW_EXCLUSIVE is not None else n
    end = min(end, n)

    # 5) 逐行调用
    processed = 0
    for i in range(start, end):
        row = df.iloc[i].to_dict()

        # 断点续跑：若该行8列都已有值则跳过
        if all(pd.notna(df.at[i, c]) for c in SCORE_COLUMNS):
            continue

        messages = build_messages(row)

        raw_text = ""
        parsed_scores: Dict[str, int] = {}
        rationale = ""
        ok = False
        err_msg = ""

        try:
            raw_text = call_llm(client, messages)
            obj = extract_json(raw_text)
            parsed_scores, rationale = validate_and_map_scores(obj)

            for cn_col, score in parsed_scores.items():
                df.at[i, cn_col] = int(score)
            df.at[i, "打分依据"] = rationale
            ok = True

        except Exception as e:
            err_msg = str(e)

        # 逐行写日志（可审计：messages + 原始输出 + 解析分数 + 简要依据）
        append_jsonl(LOG_JSONL_PATH, {
            "row_index": i,
            "industry_keys": {
                "细分类代码": row.get("细分类代码"),
                "细分类（日文）": row.get("细分类（日文）"),
                "细分类（中文）": row.get("细分类（中文）"),
            },
            "ok": ok,
            "error": err_msg,
            "request_messages": messages,
            "raw_response": raw_text,
            "parsed_scores_cn": parsed_scores,
            "rationale": rationale,
        })

        processed += 1

        # 过程落盘
        if processed % FLUSH_EVERY_N_ROWS == 0:
            df.to_csv(OUTPUT_CSV_PATH, index=False, encoding="utf-8-sig")

        if SLEEP_SECONDS > 0:
            time.sleep(SLEEP_SECONDS)

    # 6) 最终输出
    df.to_csv(OUTPUT_CSV_PATH, index=False, encoding="utf-8-sig")
    print(f"完成：输出CSV -> {OUTPUT_CSV_PATH}")
    print(f"完成：日志JSONL -> {LOG_JSONL_PATH}")


if __name__ == "__main__":
    main()
