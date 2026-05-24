export type ConditionField =
  | 'title'
  | 'content'
  | 'author'
  | 'source'
  | 'publication_title'
  | 'url'
  | 'doi'
  | 'tag'

export type ConditionOperator = 'contains' | 'equals' | 'starts_with'

export interface ComplexQueryCondition {
  field: ConditionField
  operator: ConditionOperator
  value: string
  negated: boolean
}

export interface ComplexQueryGroup {
  operator: 'AND' | 'OR'
  conditions: ComplexQueryCondition[]
  groups: ComplexQueryGroup[]
}

export interface ComplexQuery {
  root: ComplexQueryGroup
}

export function createEmptyGroup(operator: 'AND' | 'OR' = 'AND'): ComplexQueryGroup {
  return {
    operator,
    conditions: [],
    groups: [],
  }
}

export function createEmptyCondition(): ComplexQueryCondition {
  return {
    field: 'title',
    operator: 'contains',
    value: '',
    negated: false,
  }
}