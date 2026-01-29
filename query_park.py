#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自定义园区查询脚本
用法示例：
    python query_park.py --city 柳州 --industries 汽车,机械
    python query_park.py --province 天津 --city 天津 --district 武清 --park_name 武清开发区
    python query_park.py --scenario_id my-park --city 上海 --industries 电子信息,新能源
"""

import argparse
import os
from multi_energy_agent.runner import run_scenario


def main():
    parser = argparse.ArgumentParser(
        description="EcoBrain - 多能源园区低碳规划查询工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 查询柳州市汽车产业园区
  python query_park.py --city 柳州 --industries 汽车,机械
  
  # 查询天津武清开发区
  python query_park.py --province 天津 --city 天津 --district 武清 --park_name 武清开发区
  
  # 查询上海电子信息产业园区
  python query_park.py --scenario_id shanghai-electronics --city 上海 --industries 电子信息,新能源
  
  # 查询广东省制造业园区
  python query_park.py --province 广东 --industries 制造,高新技术
        """
    )
    
    # 场景配置
    parser.add_argument(
        "--scenario_id",
        type=str,
        default=None,
        help="场景 ID（默认自动生成）"
    )
    
    parser.add_argument(
        "--baseline_year",
        type=int,
        default=2023,
        help="基准年份（默认 2023）"
    )
    
    # 地理位置
    parser.add_argument(
        "--province",
        type=str,
        default="",
        help="省份名称（如：天津、广东）"
    )
    
    parser.add_argument(
        "--city",
        type=str,
        default="",
        help="城市名称（如：柳州、天津、上海）"
    )
    
    parser.add_argument(
        "--district",
        type=str,
        default="",
        help="区县名称（如：武清、浦东）"
    )
    
    parser.add_argument(
        "--park_name",
        type=str,
        default="",
        help="园区名称关键词（如：武清开发区、高新区）"
    )
    
    # 产业关键词
    parser.add_argument(
        "--industries",
        type=str,
        default="",
        help="产业关键词，逗号分隔（如：汽车,机械,电子信息）"
    )
    
    args = parser.parse_args()
    
    # 构建 metadata
    metadata = {}
    if args.province:
        metadata["province"] = args.province
    if args.city:
        metadata["city"] = args.city
    if args.district:
        metadata["district"] = args.district
    if args.park_name:
        metadata["park_name"] = args.park_name
    
    # 解析产业关键词
    if args.industries:
        industries = [i.strip() for i in args.industries.split(",") if i.strip()]
        if industries:
            metadata["industry_keywords"] = industries
    
    # 自动生成 scenario_id
    if args.scenario_id:
        scenario_id = args.scenario_id
    else:
        # 根据输入自动生成
        parts = []
        if args.city:
            parts.append(args.city)
        elif args.province:
            parts.append(args.province)
        if args.district:
            parts.append(args.district)
        if args.park_name:
            parts.append(args.park_name.replace("开发区", "").replace("高新区", ""))
        
        if parts:
            scenario_id = "-".join(parts)
        else:
            scenario_id = "custom-park"
    
    # 显示配置
    print("=" * 60)
    print("EcoBrain - 多能源园区低碳规划查询")
    print("=" * 60)
    print(f"场景 ID: {scenario_id}")
    print(f"基准年份: {args.baseline_year}")
    if metadata:
        print("\n查询条件:")
        for key, value in metadata.items():
            print(f"  {key}: {value}")
    else:
        print("\n⚠️  未指定查询条件，将使用默认配置")
    print("=" * 60)
    print()
    
    # 运行场景
    try:
        state = run_scenario(
            selection={"metadata": metadata},
            scenario={
                "scenario_id": scenario_id,
                "baseline_year": args.baseline_year,
                "description": f"{args.city or args.province or ''}园区低碳规划"
            },
            inputs={}
        )
        
        # 输出结果
        report_path = state["envelopes"]["report"]["artifacts"]["report_path"]
        report_pdf = state["envelopes"]["report"]["artifacts"]["report_pdf_path"]
        
        print()
        print("=" * 60)
        print("✅ 报告生成完成！")
        print("=" * 60)
        print(f"📄 Markdown 报告: {report_path}")
        print(f"📕 PDF 报告: {report_pdf}")
        print(f"📁 输出目录: outputs/{scenario_id}/")
        print("=" * 60)
        
    except Exception as e:
        print()
        print("=" * 60)
        print("❌ 运行失败")
        print("=" * 60)
        print(f"错误信息: {e}")
        print()
        print("请检查:")
        print("  1. DeepSeek API Key 是否配置正确")
        print("  2. 网络连接是否正常")
        print("  3. 依赖包是否安装完整")
        print("=" * 60)
        raise


if __name__ == "__main__":
    main()
