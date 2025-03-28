import logging
from typing import Dict, Any, List, Optional
import json

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser

from core.langchain_utils import get_llm, create_prompt_template, SNOWFLAKE_SYSTEM_TEMPLATE
from core.models import TimeRange, AgentResponse, AgentType
from services.snowflake_service import SnowflakeService

logger = logging.getLogger(__name__)

class SnowflakeAgent:
    def __init__(self):
        """初始化Snowflake代理和Snowflake服务"""
        self.snowflake_service = SnowflakeService()
        self.llm = get_llm(temperature=0.2)
        
    async def process_query(self, query: str, time_range: TimeRange) -> AgentResponse:
        """
        处理使用Snowflake数据的查询
        
        Args:
            query: 用户查询
            time_range: 时间范围过滤
            
        Returns:
            带有内容和元数据的代理响应
        """
        try:
            # 获取指定时间范围的估值指标
            metrics = self.snowflake_service.get_valuation_metrics(time_range)
            
            if not metrics:
                return AgentResponse(
                    agent_type=AgentType.SNOWFLAKE,
                    content="在指定的时间范围内无法找到NVIDIA的估值指标数据。请尝试不同的时间范围。"
                )
            
            # 生成可视化图表
            charts = self.snowflake_service.generate_metrics_charts(time_range)
            
            # 提取关键指标和趋势
            key_metrics_summary = self._extract_key_metrics(metrics)
            
            # 提示模板
            human_template = """
            基于NVIDIA的财务估值指标，请对以下问题提供分析：
            
            问题: {query}
            
            时间范围: {time_range}
            
            关键财务指标:
            {key_metrics}
            
            请提供一个简洁的分析，重点关注以下方面：
            1. 在此期间NVIDIA的估值变化
            2. 任何显著的财务趋势或异常值
            3. 相关的市场背景或行业对比（如有）
            4. 对投资者的含义
            
            回答要简明扼要，为非金融专业人士提供见解。
            """
            
            prompt = create_prompt_template(
                system_template=SNOWFLAKE_SYSTEM_TEMPLATE,
                human_template=human_template
            )
            
            # 生成响应
            response = await self.llm.ainvoke(
                prompt.format_messages(
                    query=query,
                    time_range=f"{time_range.start_quarter} 到 {time_range.end_quarter}",
                    key_metrics=key_metrics_summary
                )
            )
            
            return AgentResponse(
                agent_type=AgentType.SNOWFLAKE,
                content=response.content,
                data={
                    "charts": charts,
                    "metrics_count": len(metrics),
                    "time_range": {
                        "start": time_range.start_quarter,
                        "end": time_range.end_quarter
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Snowflake代理错误: {e}")
            return AgentResponse(
                agent_type=AgentType.SNOWFLAKE,
                content=f"分析NVIDIA估值指标时遇到错误: {str(e)}"
            )
    
    def _extract_key_metrics(self, metrics: List[Any]) -> str:
        """从指标数据中提取关键信息和趋势"""
        
        if not metrics or len(metrics) == 0:
            return "无可用数据"
            
        # 排序指标（按年份和季度）
        sorted_metrics = sorted(metrics, key=lambda x: (x.year, x.quarter))
        
        # 计算变化和趋势
        summary_lines = []
        
        # 添加时间范围
        first = sorted_metrics[0]
        last = sorted_metrics[-1]
        summary_lines.append(f"分析期间: {first.quarter_label} 到 {last.quarter_label}")
        
        # 市值变化
        market_cap_change = ((last.market_cap / first.market_cap) - 1) * 100
        summary_lines.append(f"市值: {self._format_value(last.market_cap)} (变化: {market_cap_change:.1f}%)")
        
        # 静态市盈率和预期市盈率
        summary_lines.append(f"当前静态市盈率: {last.trailing_pe:.2f} (期初: {first.trailing_pe:.2f})")
        summary_lines.append(f"当前预期市盈率: {last.forward_pe:.2f} (期初: {first.forward_pe:.2f})")
        
        # 市销率和市净率
        summary_lines.append(f"当前市销率: {last.price_to_sales:.2f} (期初: {first.price_to_sales:.2f})")
        summary_lines.append(f"当前市净率: {last.price_to_book:.2f} (期初: {first.price_to_book:.2f})")
        
        # 确定趋势方向
        if len(sorted_metrics) >= 3:
            # 市盈率趋势
            pe_values = [m.trailing_pe for m in sorted_metrics]
            pe_trend = self._determine_trend(pe_values)
            summary_lines.append(f"市盈率趋势: {pe_trend}")
            
            # 市销率趋势
            ps_values = [m.price_to_sales for m in sorted_metrics]
            ps_trend = self._determine_trend(ps_values)
            summary_lines.append(f"市销率趋势: {ps_trend}")
        
        return "\n".join(summary_lines)
    
    def _determine_trend(self, values: List[float]) -> str:
        """确定数值序列的趋势方向"""
        if len(values) < 2:
            return "数据不足以确定趋势"
            
        # 计算第一个和最后一个值的差异
        first_last_diff = values[-1] - values[0]
        
        # 计算连续差异的符号
        diffs = [values[i+1] - values[i] for i in range(len(values)-1)]
        pos_diffs = sum(1 for d in diffs if d > 0)
        neg_diffs = sum(1 for d in diffs if d < 0)
        
        # 基于差异确定总体趋势
        if pos_diffs > neg_diffs * 2:
            return "明显上升"
        elif pos_diffs > neg_diffs:
            return "总体上升，有波动"
        elif neg_diffs > pos_diffs * 2:
            return "明显下降"
        elif neg_diffs > pos_diffs:
            return "总体下降，有波动"
        else:
            return "相对稳定，有波动"
    
    def _format_value(self, value: float) -> str:
        """格式化大数值（如市值）"""
        if value >= 1e12:
            return f"{value/1e12:.2f}万亿美元"
        elif value >= 1e9:
            return f"{value/1e9:.2f}十亿美元"
        elif value >= 1e6:
            return f"{value/1e6:.2f}百万美元"
        else:
            return f"{value:.2f}美元"