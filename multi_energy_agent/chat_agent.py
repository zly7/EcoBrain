"""
对话式 Agent - 通过自然语言对话查询园区信息并生成报告
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from .llm import StructuredLLMClient
from .runner import run_scenario
from .utils.logging import RunContext


class ChatAgent:
    """对话式 Agent，支持自然语言查询和报告生成"""

    def __init__(self, llm: Optional[StructuredLLMClient] = None, run_context: Optional[RunContext] = None):
        self.run_context = run_context
        self.llm = llm or StructuredLLMClient(run_context=run_context)
        self.conversation_history: List[Dict[str, str]] = []
        self.current_scenario: Optional[Dict[str, Any]] = None
        print("[ChatAgent] Initialized")
    
    def chat(self, user_message: str) -> str:
        """处理用户消息并返回回复"""
        print(f"[ChatAgent] Processing message: {user_message[:50]}...")
        # 添加到对话历史
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # 分析用户意图
        intent = self._analyze_intent(user_message)
        
        # 根据意图执行相应操作
        if intent["type"] == "query_park":
            response = self._handle_park_query(intent)
        elif intent["type"] == "generate_report":
            response = self._handle_report_generation(intent)
        elif intent["type"] == "ask_question":
            response = self._handle_question(intent)
        elif intent["type"] == "general_chat":
            response = self._handle_general_chat(user_message)
        else:
            response = "抱歉，我没有理解您的意思。您可以：\n1. 查询园区信息（如：查询柳州市汽车产业园区）\n2. 生成低碳规划报告（如：生成柳州市的报告）\n3. 询问已生成报告的问题"
        
        # 添加到对话历史
        self.conversation_history.append({
            "role": "assistant",
            "content": response
        })
        
        return response
    
    def _analyze_intent(self, message: str) -> Dict[str, Any]:
        """分析用户意图"""
        message_lower = message.lower()
        
        # 先用规则快速判断常见模式
        intent = self._quick_intent_match(message, message_lower)
        if intent:
            return intent
        
        # 复杂情况使用 LLM
        system_prompt = """你是一个意图识别专家，负责分析用户消息并识别意图。

意图类型：
1. query_park - 查询园区信息
   - 包含地理位置（省/市/区县）的查询
   - 询问某地有多少园区、什么园区
   - 例如：广西有多少园区、柳州市汽车产业园区、天津武清开发区怎么样
   
2. generate_report - 生成报告
   - 明确要求生成报告、规划、分析
   - 例如：生成报告、帮我做一份规划、分析一下某某园区
   
3. ask_question - 询问已生成报告的问题
   - 询问具体的措施、排放、数据等
   - 前提是已经有报告
   - 例如：有哪些措施、排放是多少、需要什么数据
   
4. general_chat - 一般对话
   - 问候、感谢、询问功能等
   - 例如：你好、谢谢、能做什么

**重要规则**：
- 只要提到地理位置（省/市/区县/园区名），优先判断为 query_park
- 只有在明确要求"生成"、"做"、"分析"时才是 generate_report
- ask_question 仅用于询问已有报告的具体问题

返回 JSON 格式：
{
  "type": "意图类型",
  "province": "省份（如果提到）",
  "city": "城市（如果提到）",
  "district": "区县（如果提到）",
  "park_name": "园区名称（如果提到）",
  "industries": ["产业1", "产业2"],
  "question": "具体问题（如果是 ask_question）"
}"""

        user_prompt = f"用户消息：{message}\n\n请分析意图并提取信息。"
        
        fallback = json.dumps({
            "type": "general_chat",
            "province": "",
            "city": "",
            "district": "",
            "park_name": "",
            "industries": [],
            "question": ""
        }, ensure_ascii=False)
        
        try:
            print("[ChatAgent] Calling LLM for intent analysis...")
            response = self.llm.markdown(system_prompt, user_prompt, fallback=fallback)
            print(f"[ChatAgent] LLM response received, length: {len(response)}")
            # 提取 JSON
            json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
            if json_match:
                intent = json.loads(json_match.group())
            else:
                intent = json.loads(fallback)
        except Exception:
            intent = json.loads(fallback)
        
        return intent
    
    def _quick_intent_match(self, message: str, message_lower: str) -> Optional[Dict[str, Any]]:
        """快速匹配常见意图模式"""
        
        # 1. 一般对话（最优先）
        greetings = ["你好", "hello", "hi", "您好"]
        thanks = ["谢谢", "感谢", "thank"]
        help_words = ["能做什么", "功能", "帮助", "怎么用"]
        
        if any(word in message_lower for word in greetings):
            return {"type": "general_chat", "province": "", "city": "", "district": "", 
                   "park_name": "", "industries": [], "question": ""}
        
        if any(word in message_lower for word in thanks):
            return {"type": "general_chat", "province": "", "city": "", "district": "", 
                   "park_name": "", "industries": [], "question": ""}
        
        if any(word in message_lower for word in help_words):
            return {"type": "general_chat", "province": "", "city": "", "district": "", 
                   "park_name": "", "industries": [], "question": ""}
        
        # 2. 查询园区（包含地理位置）
        # 提取省份
        provinces = ["广西", "广东", "天津", "上海", "北京", "浙江", "江苏", "山东", 
                    "河北", "河南", "湖北", "湖南", "四川", "重庆", "陕西", "福建",
                    "安徽", "江西", "辽宁", "吉林", "黑龙江", "内蒙古", "山西",
                    "甘肃", "青海", "宁夏", "新疆", "西藏", "云南", "贵州", "海南"]
        
        # 提取城市
        cities = ["柳州", "武清", "浦东", "深圳", "杭州", "苏州", "南京", "成都",
                 "西安", "武汉", "长沙", "郑州", "济南", "青岛", "大连", "沈阳",
                 "广州", "东莞", "佛山", "珠海", "中山", "惠州", "江门", "肇庆",
                 "天津", "上海", "北京", "重庆", "宁波", "温州", "无锡", "常州",
                 "厦门", "福州", "泉州", "合肥", "南昌", "长春", "哈尔滨", "石家庄",
                 "太原", "呼和浩特", "兰州", "西宁", "银川", "乌鲁木齐", "拉萨",
                 "昆明", "贵阳", "南宁", "海口", "三亚"]
        
        # 查询关键词
        query_keywords = ["有多少", "多少个", "哪些", "什么", "查询", "了解", "介绍"]
        park_keywords = ["园区", "开发区", "高新区", "工业园", "产业园"]
        
        province = ""
        city = ""
        industries = []
        
        # 检查是否包含地理位置
        for p in provinces:
            if p in message:
                province = p
                break
        
        for c in cities:
            if c in message:
                city = c
                break
        
        # 提取产业关键词
        industry_keywords = ["汽车", "机械", "电子", "信息", "制造", "高新技术", 
                           "新能源", "生物医药", "化工", "纺织", "食品"]
        for ind in industry_keywords:
            if ind in message:
                industries.append(ind)
        
        # 如果包含地理位置或园区关键词，判断为查询
        has_location = province or city
        has_park_keyword = any(kw in message for kw in park_keywords)
        has_query_keyword = any(kw in message for kw in query_keywords)
        
        if has_location or (has_park_keyword and has_query_keyword):
            return {
                "type": "query_park",
                "province": province,
                "city": city,
                "district": "",
                "park_name": "",
                "industries": industries,
                "question": ""
            }
        
        # 3. 生成报告（明确的生成动作）
        generate_keywords = ["生成", "做", "制作", "编写", "分析", "规划"]
        report_keywords = ["报告", "规划", "方案", "分析"]
        
        has_generate = any(kw in message for kw in generate_keywords)
        has_report = any(kw in message for kw in report_keywords)
        
        if has_generate or has_report:
            return {
                "type": "generate_report",
                "province": province,
                "city": city,
                "district": "",
                "park_name": "",
                "industries": industries,
                "question": ""
            }
        
        # 4. 询问问题（关于措施、排放等）
        question_keywords = ["措施", "建议", "方案", "排放", "碳", "基线", 
                           "政策", "补贴", "支持", "数据", "缺口"]
        
        if any(kw in message for kw in question_keywords):
            return {
                "type": "ask_question",
                "province": "",
                "city": "",
                "district": "",
                "park_name": "",
                "industries": [],
                "question": message
            }
        
        # 无法快速匹配，返回 None 让 LLM 处理
        return None
    
    def _handle_park_query(self, intent: Dict[str, Any]) -> str:
        """处理园区查询"""
        print(f"[ChatAgent] Handling park query: {intent}")
        # 提取参数
        province = intent.get("province", "")
        city = intent.get("city", "")
        district = intent.get("district", "")
        park_name = intent.get("park_name", "")
        industries = intent.get("industries", [])

        if not city and not province:
            return "请告诉我您想查询哪个城市或省份的园区？例如：\n- 查询柳州市汽车产业园区\n- 天津武清开发区\n- 上海电子信息产业园\n- 广西有多少个产业园区"

        # 尝试直接查询统计信息
        try:
            print("[ChatAgent] Loading tool registry...")
            from .tools import default_tool_registry
            tools = default_tool_registry()
            print("[ChatAgent] Tool registry loaded")

            # 构建查询条件
            filters = {
                "province": province,
                "city": city,
                "district": district,
                "park_name_contains": park_name,
                "industry_keywords": industries,
            }

            # 调用 FHD 工具查询
            print(f"[ChatAgent] Calling load_fhd_back_data with filters: {filters}")
            fhd_result = tools.call(
                "load_fhd_back_data",
                {
                    "output_dir": "outputs/temp_query",
                    "filters": filters,
                    "max_matched_rows": 5000,
                    "include_aoi_summary": True,
                    "aoi_compute_area_km2": False,
                }
            )
            print(f"[ChatAgent] FHD query completed, ok={fhd_result.get('ok')}")

            if fhd_result.get("ok"):
                fhd_data = fhd_result.get("data", {})
                metrics = fhd_data.get("metrics", {})
                
                # 构建回复
                location = ""
                if province:
                    location += province
                if city:
                    location += city
                if district:
                    location += district
                
                matched_parks = metrics.get('matched_parks', 0)
                total_parks = metrics.get('total_parks', 0)
                
                # 如果没有匹配结果，给出友好提示
                if matched_parks == 0:
                    response = f"**{location}园区查询结果：**\n\n"
                    response += f"📊 在我们的数据库中（共 {total_parks:,} 个园区），"
                    
                    if city and not province:
                        response += f"暂未找到明确标注为「{city}」的园区。\n\n"
                        response += "💡 **可能的原因：**\n"
                        response += f"1. 数据库中可能使用「{city}市」或其他表述\n"
                        response += f"2. {city}的园区可能归属于更大的行政区划\n"
                        response += "3. 数据尚未完全覆盖该地区\n\n"
                        response += "🔍 **建议：**\n"
                        response += f"- 尝试查询：「广东省{city}」或「{city}市」\n"
                        response += "- 或者直接生成报告，系统会尽可能匹配相关数据\n"
                    else:
                        response += f"暂未找到符合条件的园区。\n\n"
                        response += "💡 **建议：**\n"
                        response += "- 尝试放宽查询条件（如只查询省份）\n"
                        response += "- 或者直接生成报告，系统会使用行业平均数据\n"
                    
                    response += "\n您想要：\n"
                    response += "1. 调整查询条件重新查询\n"
                    response += "2. 直接生成低碳规划报告（使用行业平均数据）\n"
                    
                    # 保存当前查询参数
                    self.current_scenario = {
                        "province": province,
                        "city": city,
                        "district": district,
                        "park_name": park_name,
                        "industries": industries
                    }
                    
                    return response
                
                # 有匹配结果，显示统计信息
                response = f"**{location}园区统计信息：**\n\n"
                response += f"📊 **总体情况**\n"
                response += f"- 全国园区总数：{total_parks:,} 个\n"
                response += f"- {location}匹配园区：{matched_parks:,} 个\n\n"
                
                # 产业分布
                top_industries = metrics.get("matched_industry_distribution_top", [])
                if top_industries:
                    response += f"🏭 **主要产业分布（Top 10）**\n"
                    for name, count in top_industries[:10]:
                        response += f"- {name}: {count} 个\n"
                    response += "\n"
                
                # 园区级别
                top_levels = metrics.get("matched_level_distribution_top", [])
                if top_levels:
                    response += f"🏆 **园区级别分布**\n"
                    for name, count in top_levels[:5]:
                        response += f"- {name}: {count} 个\n"
                    response += "\n"
                
                response += "---\n\n"
                response += "💡 **下一步您可以：**\n"
                response += "1. 生成详细的低碳规划报告\n"
                response += "2. 查询特定产业的园区\n"
                response += "3. 了解某个具体园区的情况\n\n"
                response += "请告诉我您需要什么？"
                
                # 保存当前查询参数
                self.current_scenario = {
                    "province": province,
                    "city": city,
                    "district": district,
                    "park_name": park_name,
                    "industries": industries
                }
                
                return response
            
        except Exception as e:
            # 查询失败，降级到原来的逻辑
            pass
        
        # 降级：构建查询描述
        location = ""
        if province:
            location += province
        if city:
            location += city
        if district:
            location += district
        if park_name:
            location += park_name
        
        industries_str = "、".join(industries) if industries else "综合产业"
        
        response = f"好的，我将为您查询 **{location}** 的园区信息"
        if industries:
            response += f"，重点关注 **{industries_str}** 产业"
        response += "。\n\n"
        
        # 询问是否生成报告
        response += "我可以为您：\n"
        response += "1. 生成完整的低碳规划报告（包含现状分析、措施建议、政策支持等）\n"
        response += "2. 先查看园区基本信息\n\n"
        response += "请问您需要哪种服务？"
        
        # 保存当前查询参数
        self.current_scenario = {
            "province": province,
            "city": city,
            "district": district,
            "park_name": park_name,
            "industries": industries
        }
        
        return response
    
    def _handle_report_generation(self, intent: Dict[str, Any]) -> str:
        """处理报告生成"""
        # 如果有当前场景，使用它；否则从 intent 提取
        if self.current_scenario:
            params = self.current_scenario
        else:
            params = {
                "province": intent.get("province", ""),
                "city": intent.get("city", ""),
                "district": intent.get("district", ""),
                "park_name": intent.get("park_name", ""),
                "industries": intent.get("industries", [])
            }
        
        # 检查是否有足够的信息
        if not params.get("city") and not params.get("province"):
            return "请先告诉我您想分析哪个园区？例如：\n- 柳州市汽车产业园区\n- 天津武清开发区\n- 上海电子信息产业园"
        
        # 生成场景 ID
        scenario_id_parts = []
        if params.get("city"):
            scenario_id_parts.append(params["city"].replace("市", ""))
        elif params.get("province"):
            scenario_id_parts.append(params["province"].replace("省", ""))
        if params.get("district"):
            scenario_id_parts.append(params["district"])
        if params.get("park_name"):
            scenario_id_parts.append(params["park_name"].replace("开发区", "").replace("高新区", ""))
        
        scenario_id = "-".join(scenario_id_parts) if scenario_id_parts else "custom-park"
        
        # 构建描述
        location = ""
        if params.get("province"):
            location += params["province"]
        if params.get("city"):
            location += params["city"]
        if params.get("district"):
            location += params["district"]
        if params.get("park_name"):
            location += params["park_name"]
        
        response = f"正在为 **{location}** 生成低碳规划报告...\n\n"
        response += "这个过程大约需要 2-3 分钟，包括：\n"
        response += "1. 数据接入与分析\n"
        response += "2. 园区画像与能源倾向推断\n"
        response += "3. 措施筛选与政策匹配\n"
        response += "4. 专业报告生成\n\n"
        
        try:
            # 构建 metadata
            metadata = {}
            if params.get("province"):
                metadata["province"] = params["province"]
            if params.get("city"):
                metadata["city"] = params["city"]
            if params.get("district"):
                metadata["district"] = params["district"]
            if params.get("park_name"):
                metadata["park_name"] = params["park_name"]
            if params.get("industries"):
                metadata["industry_keywords"] = params["industries"]
            
            # 运行场景
            state = run_scenario(
                selection={"metadata": metadata},
                scenario={
                    "scenario_id": scenario_id,
                    "baseline_year": 2023,
                    "description": f"{location}低碳规划"
                },
                inputs={}
            )
            
            # 获取结果
            report_path = state["envelopes"]["report"]["artifacts"]["report_path"]
            report_pdf = state["envelopes"]["report"]["artifacts"]["report_pdf_path"]
            
            response += "✅ **报告生成完成！**\n\n"
            response += f"📄 Markdown 报告：`{report_path}`\n"
            response += f"📕 PDF 报告：`{report_pdf}`\n\n"
            
            # 提取关键信息
            measures = state["envelopes"]["insight"]["artifacts"].get("measures", [])
            response += f"**核心发现：**\n"
            response += f"- 推荐措施：{len(measures)} 项\n"
            
            if measures:
                response += f"\n**Top 3 措施：**\n"
                for i, m in enumerate(measures[:3], 1):
                    response += f"{i}. {m.get('name')} (评分: {m.get('applicability_score'):.2f})\n"
            
            response += f"\n您可以继续询问：\n"
            response += "- 有哪些减排措施？\n"
            response += "- 基线排放是多少？\n"
            response += "- 有哪些政策支持？\n"
            response += "- 需要补充哪些数据？"
            
            # 保存场景信息供后续问答
            self.current_scenario = {
                **params,
                "scenario_id": scenario_id,
                "state": state
            }
            
        except Exception as e:
            response += f"❌ **报告生成失败**\n\n"
            response += f"错误信息：{str(e)}\n\n"
            response += "请检查：\n"
            response += "1. DeepSeek API Key 是否配置正确\n"
            response += "2. 网络连接是否正常\n"
            response += "3. 输入参数是否完整"
        
        return response
    
    def _handle_question(self, intent: Dict[str, Any]) -> str:
        """处理问题询问"""
        question = intent.get("question", "")
        
        if not self.current_scenario or not self.current_scenario.get("state"):
            return "请先生成报告，然后我可以回答相关问题。\n\n例如：生成柳州市汽车产业园区的报告"
        
        # 从当前场景获取信息
        state = self.current_scenario["state"]
        
        # 提取关键信息
        insight_artifacts = state["envelopes"]["insight"]["artifacts"]
        measures = insight_artifacts.get("measures", [])
        park_profile = insight_artifacts.get("park_profile", {})
        energy_tendency = insight_artifacts.get("energy_tendency", {})
        
        # 根据问题类型回答
        question_lower = question.lower()
        
        if any(kw in question_lower for kw in ["措施", "建议", "方案"]):
            response = f"根据分析，推荐以下 {len(measures)} 项措施：\n\n"
            for i, m in enumerate(measures[:5], 1):
                response += f"**{i}. {m.get('name')}**\n"
                response += f"   - 适用性评分：{m.get('applicability_score'):.2f}\n"
                response += f"   - 说明：{m.get('explain', '暂无')}\n"
                if m.get('data_needs'):
                    response += f"   - 需要数据：{', '.join(m.get('data_needs', [])[:3])}\n"
                response += "\n"
            
            if len(measures) > 5:
                response += f"...（还有 {len(measures) - 5} 项措施，详见完整报告）"
        
        elif any(kw in question_lower for kw in ["排放", "碳", "基线"]):
            # 估算基线排放
            matched_parks = park_profile.get("matched_parks", 0)
            estimated_emissions = matched_parks * 50000 if matched_parks > 0 else 850000
            
            response = f"**基线排放估算：**\n\n"
            response += f"- 总排放：约 {estimated_emissions:,} tCO2/年\n"
            response += f"- Scope 1（直接排放）：约 {int(estimated_emissions * 0.4):,} tCO2\n"
            response += f"- Scope 2（间接排放）：约 {int(estimated_emissions * 0.6):,} tCO2\n\n"
            response += "⚠️ 注意：这是基于园区数量和行业平均值的粗略估算，实际排放需要通过能源审计确定。"
        
        elif any(kw in question_lower for kw in ["政策", "补贴", "支持"]):
            eco_blocks = insight_artifacts.get("eco_kg_evidence", [])
            policy_count = sum(len(b.get("snippets", [])) for b in eco_blocks)
            
            response = f"**政策支持：**\n\n"
            response += f"检索到 {policy_count} 条相关政策条款，主要包括：\n\n"
            
            for i, block in enumerate(eco_blocks[:3], 1):
                query = block.get("query", "")
                snippets = block.get("snippets", [])
                if snippets:
                    top_snippet = snippets[0]
                    response += f"**{i}. {query}**\n"
                    response += f"   来源：{top_snippet.get('source', '')}\n"
                    response += f"   内容：{top_snippet.get('text', '')[:100]}...\n\n"
        
        elif any(kw in question_lower for kw in ["数据", "缺口", "需要"]):
            # 收集所有数据需求
            all_data_needs = set()
            for m in measures:
                all_data_needs.update(m.get("data_needs", []))
            
            response = f"**关键数据缺口：**\n\n"
            high_priority = ["负荷曲线", "能耗台账", "设备清单", "屋顶面积", "电价数据"]
            
            for i, gap in enumerate(high_priority, 1):
                if any(gap in need for need in all_data_needs):
                    response += f"{i}. {gap}\n"
                    response += f"   - 影响：精确的技术方案设计和经济性分析\n"
                    response += f"   - 获取途径：{'电力公司' if '电' in gap else '现场调研或企业提供'}\n\n"
        
        else:
            # 通用回答
            response = f"关于「{question}」，我建议您查看完整报告以获取详细信息。\n\n"
            response += "您也可以询问：\n"
            response += "- 有哪些减排措施？\n"
            response += "- 基线排放是多少？\n"
            response += "- 有哪些政策支持？\n"
            response += "- 需要补充哪些数据？"
        
        return response
    
    def _handle_general_chat(self, message: str) -> str:
        """处理一般对话"""
        message_lower = message.lower()
        
        if any(kw in message_lower for kw in ["你好", "hello", "hi"]):
            return """您好！我是 EcoBrain 多能源园区低碳规划助手。

我可以帮您：
1. 📊 查询全国 10 万+ 园区信息
2. 📝 生成专业的低碳规划报告
3. 💡 提供减排措施建议
4. 📋 匹配相关政策支持

请告诉我您想查询哪个园区？例如：
- 柳州市汽车产业园区
- 天津武清开发区
- 上海电子信息产业园"""
        
        elif any(kw in message_lower for kw in ["谢谢", "感谢", "thank"]):
            return "不客气！如果还有其他问题，随时告诉我。"
        
        elif any(kw in message_lower for kw in ["能做什么", "功能", "帮助"]):
            return """我的核心功能：

**1. 园区查询**
   - 覆盖全国 104,127 个产业园区
   - 支持按省份、城市、产业筛选

**2. 报告生成**
   - 园区现状分析
   - 能源需求特征
   - 减排措施建议
   - 政策支持梳理
   - 经济效益分析

**3. 智能问答**
   - 措施详情
   - 排放数据
   - 政策支持
   - 数据需求

请告诉我您想查询哪个园区？"""
        
        else:
            return """我没有完全理解您的意思。

您可以：
1. 查询园区信息（如：查询柳州市汽车产业园区）
2. 生成低碳规划报告（如：生成柳州市的报告）
3. 询问已生成报告的问题（如：有哪些减排措施）

请问您需要什么帮助？"""
    
    def reset(self):
        """重置对话状态"""
        self.conversation_history = []
        self.current_scenario = None
    
    def get_history(self) -> List[Dict[str, str]]:
        """获取对话历史"""
        return self.conversation_history


__all__ = ["ChatAgent"]
