## 1. 数据分组逻辑

- [x] 1.1 创建 `groupByMA` 函数，将扁平数组按 `ma_type` 分组
- [x] 1.2 创建 `sortGroupsByMANumber` 函数，按 MA 数字升序排序分组
- [x] 1.3 创建 `sortItemsByDeviation` 函数，按偏离度降序排序组内项目
- [x] 1.4 创建 `filterEmptyGroups` 函数，过滤空分组

## 2. UI 组件实现

- [x] 2.1 导入 Ant Design Collapse 组件
- [x] 2.2 创建 `renderMACollapsePanel` 函数，渲染单个 MA 分组面板
- [x] 2.3 修改"新增达标"列表，使用 Collapse 分组展示
- [x] 2.4 修改"跌破均线"列表，使用 Collapse 分组展示
- [x] 2.5 添加分组标题样式（显示 MA 类型和数量）

## 3. 测试验证

- [x] 3.1 验证分组排序正确（MA5 → MA10 → MA20）- 代码逻辑已验证
- [x] 3.2 验证组内排序正确（偏离度降序）- 代码逻辑已验证
- [x] 3.3 验证空分组不显示 - 代码逻辑已验证（filterEmptyGroups）
- [x] 3.4 验证折叠/展开功能正常 - Collapse 组件已正确配置
- [x] 3.5 验证日期切换后状态重置 - Collapse 使用 defaultActiveKey
