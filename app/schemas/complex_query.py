from typing import List, Optional
from pydantic import BaseModel


class ComplexQueryCondition(BaseModel):
    """Условие внутри сложного запроса"""
    field: str  # title, content, author, source, publication_title, url, doi, tag
    operator: str = "contains"  # contains, equals, starts_with
    value: str
    negated: bool = False  # НЕ


class ComplexQueryGroup(BaseModel):
    """Группа условий с оператором"""
    operator: str = "AND"  # AND, OR
    conditions: List[ComplexQueryCondition] = []
    groups: List["ComplexQueryGroup"] = []


# Обновляем рекурсивную ссылку
ComplexQueryGroup.model_rebuild()


class ComplexQuery(BaseModel):
    """Корень сложного запроса"""
    root: ComplexQueryGroup