## Context

每日报告页面 (`DailyReport.jsx`) 使用 Ant Design 的 `DatePicker` 组件让用户选择日期查看历史报告。当前实现存在以下问题：

1. 日期选择没有限制未来日期，用户可以选择没有数据的未来日期
2. 当用户选择的历史日期没有快照数据时，缺少引导用户生成报告的交互
3. 交易日判断依赖后端 AkShare API，可能因网络或依赖问题失败

### 技术约束

- 前端使用 React + Ant Design
- 后端使用 FastAPI + AkShare 获取交易日历
- 交易日历数据缓存在 SQLite 数据库中

## Goals / Non-Goals

**Goals:**
- 禁止用户选择未来日期
- 为无快照的历史日期提供生成报告的入口
- 改进交易日判断的错误处理

**Non-Goals:**
- 不改变现有的 API 接口
- 不修改交易日历的缓存机制
- 不添加新的数据源

## Decisions

### Decision 1: DatePicker 未来日期禁用

**选择**: 使用 `disabledDate` 属性禁用今天之后的日期

**理由**:
- Ant Design DatePicker 原生支持，实现简单
- 用户体验直观，选择时就能看到哪些日期不可选

**实现**:
```jsx
const disabledDate = (current) => {
  if (!current) return true;
  return current && current.isAfter(dayjs().endOf('day'));
};
```

### Decision 2: 无快照历史日期的交互

**选择**: 使用 `Modal.confirm` 确认对话框

**备选方案**:
1. 直接自动生成 - 可能造成意外行为
2. 跳转提示页面 - 增加用户操作步骤
3. Modal.confirm - 明确用户意图，体验流畅 ✓

**理由**:
- 用户明确知道即将发生什么操作
- 可以取消不需要的操作
- 不需要离开当前页面

**实现**:
```jsx
Modal.confirm({
  title: '该日期暂无分析报告',
  content: `是否为 ${date.format('YYYY-MM-DD')} 生成分析报告？`,
  okText: '确认生成',
  cancelText: '取消',
  onOk: () => handleGenerateSnapshots(date)
});
```

### Decision 3: 交易日判断失败的处理

**选择**: 前端显示友好提示，后端增强日志

**理由**:
- AkShare API 失败时后端已有降级逻辑（使用周末判断）
- 前端增加 loading 状态和错误提示
- 后端增加更详细的日志便于排查

## Risks / Trade-offs

### Risk: AkShare API 不可用
→ **Mitigation**: 后端已实现降级到周末判断，前端显示"交易日历数据获取中"状态

### Risk: 用户频繁选择历史日期触发大量 API 请求
→ **Mitigation**: 生成快照操作需要用户确认，避免意外触发

### Trade-off: Modal 确认增加了操作步骤
→ **接受**: 这是必要的交互，避免用户误操作
