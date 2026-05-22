from src.agent.llm import llm_client
from src.schemas import AgentStep


DEFAULT_PLAN = {
    "steps": [
        {
            "id": "step-1",
            "action": "parse_source",
            "tool": "document_parser",
            "purpose": "解析输入文件或网页，提取正文、元数据和可见表格文本。",
        },
        {
            "id": "step-2",
            "action": "extract_structure",
            "tool": "llm_extractor",
            "purpose": "根据任务目标抽取结构化字段、实体、表格与证据。",
        },
        {
            "id": "step-3",
            "action": "validate_result",
            "tool": "result_validator",
            "purpose": "检查输出完整性、一致性和证据可追溯性。",
        },
    ]
}


async def build_plan(goal: str, source_name: str) -> list[AgentStep]:
    data = await llm_client.chat_json(
        system=(
            "你是数据处理 Agent 的任务规划器。只输出 JSON，格式为 "
            '{"steps":[{"id":"step-1","action":"...","tool":"...","purpose":"..."}]}。'
        ),
        user=f"任务目标：{goal}\n输入来源：{source_name}\n请拆解为 3-6 个可执行步骤。",
        fallback=DEFAULT_PLAN.copy(),
    )
    return [AgentStep(**step) for step in data.get("steps", DEFAULT_PLAN["steps"])]
