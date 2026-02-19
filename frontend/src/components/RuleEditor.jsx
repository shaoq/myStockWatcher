/**
 * 规则编辑表单组件
 *
 * 功能：
 * - 基本信息表单（名称、类型、优先级、强度）
 * - 触发条件配置（指标、字段、操作符、目标值）
 * - 价位配置（入场价、止损价、止盈价）
 * - 表单验证
 */
import React, { useState, useEffect } from "react";
import {
  Modal,
  Form,
  Input,
  InputNumber,
  Select,
  Switch,
  Button,
  Space,
  Divider,
  Card,
  message,
} from "antd";
import { PlusOutlined, MinusCircleOutlined } from "@ant-design/icons";
import { ruleApi } from "../services/api";

const { Option } = Select;

// 指标类型配置
const INDICATOR_CONFIG = {
  MA: {
    name: "移动平均线",
    fields: ["MA5", "MA10", "MA20", "MA60"],
  },
  MACD: {
    name: "MACD",
    fields: ["DIF", "DEA", "MACD"],
  },
  RSI: {
    name: "RSI",
    fields: ["RSI"],
  },
  KDJ: {
    name: "KDJ",
    fields: ["K", "D", "J"],
  },
  Bollinger: {
    name: "布林带",
    fields: ["upper", "middle", "lower"],
  },
};

// 操作符配置
const OPERATOR_CONFIG = {
  comparison: [
    { value: "gt", label: "大于 (>)" },
    { value: "lt", label: "小于 (<)" },
    { value: "gte", label: "大于等于 (>=)" },
    { value: "lte", label: "小于等于 (<=)" },
    { value: "eq", label: "等于 (=)" },
  ],
  cross: [
    { value: "cross_above", label: "上穿" },
    { value: "cross_below", label: "下穿" },
  ],
  threshold: [
    { value: "below_threshold", label: "低于阈值" },
    { value: "above_threshold", label: "高于阈值" },
  ],
};

const RuleEditor = ({ visible, rule, onClose }) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [isEdit, setIsEdit] = useState(false);

  // 初始化表单
  useEffect(() => {
    if (visible) {
      if (rule && rule.id) {
        // 编辑模式
        setIsEdit(true);
        const conditions = typeof rule.conditions === "string"
          ? JSON.parse(rule.conditions)
          : rule.conditions;
        const priceConfig = typeof rule.price_config === "string"
          ? JSON.parse(rule.price_config)
          : rule.price_config;

        form.setFieldsValue({
          name: rule.name,
          rule_type: rule.rule_type,
          enabled: rule.enabled,
          priority: rule.priority,
          strength: rule.strength,
          conditions: conditions.conditions || conditions,
          price_config: priceConfig,
          description_template: rule.description_template,
        });
      } else {
        // 新建模式
        setIsEdit(false);
        form.resetFields();
        form.setFieldsValue({
          rule_type: rule?.rule_type || "buy",
          enabled: true,
          priority: 0,
          strength: 2,
          conditions: [{}],
          price_config: {
            entry: { type: "current" },
          },
        });
      }
    }
  }, [visible, rule, form]);

  // 提交表单
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);

      // 构建请求数据
      const data = {
        name: values.name,
        rule_type: values.rule_type,
        enabled: values.enabled,
        priority: values.priority,
        strength: values.strength,
        conditions: values.conditions,
        price_config: values.price_config,
        description_template: values.description_template,
      };

      if (isEdit) {
        await ruleApi.updateRule(rule.id, data);
        message.success("规则更新成功");
      } else {
        await ruleApi.createRule(data);
        message.success("规则创建成功");
      }

      onClose(true);
    } catch (error) {
      if (error.errorFields) {
        // 表单验证错误
        return;
      }
      message.error(`操作失败: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  // 条件字段选择器
  const renderFieldSelector = (indicator, fieldPath) => {
    const config = INDICATOR_CONFIG[indicator];
    if (!config) return null;

    return (
      <Form.Item name={[...fieldPath, "field"]} noStyle>
        <Select style={{ width: 100 }} placeholder="字段">
          {config.fields.map((f) => (
            <Option key={f} value={f}>
              {f}
            </Option>
          ))}
        </Select>
      </Form.Item>
    );
  };

  // 目标字段选择器（当 target_type=indicator 时）
  const renderTargetFieldSelector = (targetIndicator, fieldPath) => {
    const config = INDICATOR_CONFIG[targetIndicator];
    if (!config) return null;

    return (
      <Form.Item name={[...fieldPath, "target_field"]} noStyle>
        <Select style={{ width: 100 }} placeholder="目标字段">
          {config.fields.map((f) => (
            <Option key={f} value={f}>
              {f}
            </Option>
          ))}
        </Select>
      </Form.Item>
    );
  };

  return (
    <Modal
      title={isEdit ? "编辑规则" : "新建规则"}
      open={visible}
      onCancel={() => onClose(false)}
      width={800}
      footer={[
        <Button key="cancel" onClick={() => onClose(false)}>
          取消
        </Button>,
        <Button key="submit" type="primary" loading={loading} onClick={handleSubmit}>
          保存
        </Button>,
      ]}
    >
      <Form form={form} layout="vertical">
        {/* 基本信息 */}
        <Card title="基本信息" size="small" style={{ marginBottom: 16 }}>
          <Form.Item
            name="name"
            label="规则名称"
            rules={[{ required: true, message: "请输入规则名称" }]}
          >
            <Input placeholder="如：MA金叉买入" maxLength={100} />
          </Form.Item>

          <Space style={{ width: "100%" }} size="large">
            <Form.Item
              name="rule_type"
              label="规则类型"
              rules={[{ required: true }]}
            >
              <Select style={{ width: 120 }} disabled={isEdit}>
                <Option value="buy">买入</Option>
                <Option value="sell">卖出</Option>
              </Select>
            </Form.Item>

            <Form.Item name="enabled" label="启用状态" valuePropName="checked">
              <Switch checkedChildren="启用" unCheckedChildren="禁用" />
            </Form.Item>

            <Form.Item
              name="priority"
              label="优先级"
              tooltip="数值越大优先级越高"
            >
              <InputNumber min={0} max={100} style={{ width: 80 }} />
            </Form.Item>

            <Form.Item name="strength" label="信号强度">
              <Select style={{ width: 120 }}>
                {[1, 2, 3, 4, 5].map((i) => (
                  <Option key={i} value={i}>
                    {"★".repeat(i)}{"☆".repeat(5 - i)}
                  </Option>
                ))}
              </Select>
            </Form.Item>
          </Space>
        </Card>

        {/* 触发条件 */}
        <Card title="触发条件" size="small" style={{ marginBottom: 16 }}>
          <Form.List name="conditions">
            {(fields, { add, remove }) => (
              <>
                {fields.map(({ key, name, ...restField }) => (
                  <Space key={key} style={{ display: "flex", marginBottom: 8 }} align="baseline">
                    <Form.Item
                      {...restField}
                      name={[name, "indicator"]}
                      rules={[{ required: true, message: "选择指标" }]}
                    >
                      <Select style={{ width: 120 }} placeholder="指标类型">
                        {Object.entries(INDICATOR_CONFIG).map(([k, v]) => (
                          <Option key={k} value={k}>
                            {v.name}
                          </Option>
                        ))}
                      </Select>
                    </Form.Item>

                    <Form.Item shouldUpdate noStyle>
                      {({ getFieldValue }) => {
                        const indicator = getFieldValue(["conditions", name, "indicator"]);
                        return renderFieldSelector(indicator, ["conditions", name]);
                      }}
                    </Form.Item>

                    <Form.Item
                      {...restField}
                      name={[name, "operator"]}
                      rules={[{ required: true, message: "选择操作符" }]}
                    >
                      <Select style={{ width: 120 }} placeholder="操作符">
                        <Option group label="比较">
                          {OPERATOR_CONFIG.comparison.map((op) => (
                            <Option key={op.value} value={op.value}>
                              {op.label}
                            </Option>
                          ))}
                        </Option>
                        <Option group label="交叉">
                          {OPERATOR_CONFIG.cross.map((op) => (
                            <Option key={op.value} value={op.value}>
                              {op.label}
                            </Option>
                          ))}
                        </Option>
                      </Select>
                    </Form.Item>

                    <Form.Item
                      {...restField}
                      name={[name, "target_type"]}
                      rules={[{ required: true, message: "选择目标类型" }]}
                    >
                      <Select style={{ width: 100 }} placeholder="目标类型">
                        <Option value="indicator">指标</Option>
                        <Option value="value">数值</Option>
                      </Select>
                    </Form.Item>

                    <Form.Item shouldUpdate noStyle>
                      {({ getFieldValue }) => {
                        const targetType = getFieldValue(["conditions", name, "target_type"]);
                        if (targetType === "indicator") {
                          return (
                            <>
                              <Form.Item
                                {...restField}
                                name={[name, "target_indicator"]}
                                noStyle
                              >
                                <Select style={{ width: 100 }} placeholder="目标指标">
                                  {Object.entries(INDICATOR_CONFIG).map(([k, v]) => (
                                    <Option key={k} value={k}>
                                      {v.name}
                                    </Option>
                                  ))}
                                </Select>
                              </Form.Item>
                              <Form.Item shouldUpdate noStyle>
                                {({ getFieldValue }) => {
                                  const targetIndicator = getFieldValue([
                                    "conditions",
                                    name,
                                    "target_indicator",
                                  ]);
                                  return renderTargetFieldSelector(targetIndicator, [
                                    "conditions",
                                    name,
                                  ]);
                                }}
                              </Form.Item>
                            </>
                          );
                        } else if (targetType === "value") {
                          return (
                            <Form.Item
                              {...restField}
                              name={[name, "target_value"]}
                              noStyle
                            >
                              <InputNumber style={{ width: 100 }} placeholder="数值" />
                            </Form.Item>
                          );
                        }
                        return null;
                      }}
                    </Form.Item>

                    <MinusCircleOutlined onClick={() => remove(name)} />
                  </Space>
                ))}
                <Button type="dashed" onClick={() => add()} block icon={<PlusOutlined />}>
                  添加条件
                </Button>
              </>
            )}
          </Form.List>
        </Card>

        {/* 价位配置 */}
        <Card title="价位配置" size="small" style={{ marginBottom: 16 }}>
          <Form.Item label="入场价" required>
            <Space>
              <Form.Item name={["price_config", "entry", "type"]} noStyle>
                <Select style={{ width: 100 }}>
                  <Option value="indicator">指标值</Option>
                  <Option value="percentage">百分比</Option>
                  <Option value="current">当前价</Option>
                </Select>
              </Form.Item>
              <Form.Item shouldUpdate noStyle>
                {({ getFieldValue }) => {
                  const type = getFieldValue(["price_config", "entry", "type"]);
                  if (type === "indicator") {
                    return (
                      <>
                        <Form.Item name={["price_config", "entry", "indicator"]} noStyle>
                          <Select style={{ width: 100 }} placeholder="指标">
                            {Object.entries(INDICATOR_CONFIG).map(([k, v]) => (
                              <Option key={k} value={k}>
                                {v.name}
                              </Option>
                            ))}
                          </Select>
                        </Form.Item>
                        <Form.Item name={["price_config", "entry", "field"]} noStyle>
                          <Select style={{ width: 100 }} placeholder="字段">
                            {Object.values(INDICATOR_CONFIG)
                              .flatMap((c) => c.fields)
                              .map((f) => (
                                <Option key={f} value={f}>
                                  {f}
                                </Option>
                              ))}
                          </Select>
                        </Form.Item>
                      </>
                    );
                  } else if (type === "percentage") {
                    return (
                      <Form.Item name={["price_config", "entry", "value"]} noStyle>
                        <InputNumber
                          style={{ width: 100 }}
                          placeholder="如 -0.02"
                          step={0.01}
                        />
                      </Form.Item>
                    );
                  }
                  return null;
                }}
              </Form.Item>
            </Space>
          </Form.Item>

          <Form.Item label="止损价">
            <Space>
              <Form.Item name={["price_config", "stop_loss", "type"]} noStyle>
                <Select style={{ width: 100 }} allowClear placeholder="不设置">
                  <Option value="percentage">百分比</Option>
                  <Option value="indicator">指标值</Option>
                </Select>
              </Form.Item>
              <Form.Item shouldUpdate noStyle>
                {({ getFieldValue }) => {
                  const type = getFieldValue(["price_config", "stop_loss", "type"]);
                  if (type === "percentage") {
                    return (
                      <>
                        <Form.Item name={["price_config", "stop_loss", "base"]} noStyle>
                          <Select style={{ width: 100 }} placeholder="基准">
                            <Option value="entry">入场价</Option>
                            <Option value="current">当前价</Option>
                          </Select>
                        </Form.Item>
                        <Form.Item name={["price_config", "stop_loss", "value"]} noStyle>
                          <InputNumber
                            style={{ width: 100 }}
                            placeholder="如 -0.05"
                            step={0.01}
                          />
                        </Form.Item>
                      </>
                    );
                  } else if (type === "indicator") {
                    return (
                      <>
                        <Form.Item name={["price_config", "stop_loss", "indicator"]} noStyle>
                          <Select style={{ width: 100 }} placeholder="指标">
                            {Object.entries(INDICATOR_CONFIG).map(([k, v]) => (
                              <Option key={k} value={k}>
                                {v.name}
                              </Option>
                            ))}
                          </Select>
                        </Form.Item>
                        <Form.Item name={["price_config", "stop_loss", "field"]} noStyle>
                          <Select style={{ width: 100 }} placeholder="字段">
                            {Object.values(INDICATOR_CONFIG)
                              .flatMap((c) => c.fields)
                              .map((f) => (
                                <Option key={f} value={f}>
                                  {f}
                                </Option>
                              ))}
                          </Select>
                        </Form.Item>
                      </>
                    );
                  }
                  return null;
                }}
              </Form.Item>
            </Space>
          </Form.Item>

          <Form.Item label="止盈价">
            <Space>
              <Form.Item name={["price_config", "take_profit", "type"]} noStyle>
                <Select style={{ width: 100 }} allowClear placeholder="不设置">
                  <Option value="percentage">百分比</Option>
                  <Option value="indicator">指标值</Option>
                </Select>
              </Form.Item>
              <Form.Item shouldUpdate noStyle>
                {({ getFieldValue }) => {
                  const type = getFieldValue(["price_config", "take_profit", "type"]);
                  if (type === "percentage") {
                    return (
                      <>
                        <Form.Item name={["price_config", "take_profit", "base"]} noStyle>
                          <Select style={{ width: 100 }} placeholder="基准">
                            <Option value="entry">入场价</Option>
                            <Option value="current">当前价</Option>
                          </Select>
                        </Form.Item>
                        <Form.Item name={["price_config", "take_profit", "value"]} noStyle>
                          <InputNumber
                            style={{ width: 100 }}
                            placeholder="如 0.08"
                            step={0.01}
                          />
                        </Form.Item>
                      </>
                    );
                  } else if (type === "indicator") {
                    return (
                      <>
                        <Form.Item name={["price_config", "take_profit", "indicator"]} noStyle>
                          <Select style={{ width: 100 }} placeholder="指标">
                            {Object.entries(INDICATOR_CONFIG).map(([k, v]) => (
                              <Option key={k} value={k}>
                                {v.name}
                              </Option>
                            ))}
                          </Select>
                        </Form.Item>
                        <Form.Item name={["price_config", "take_profit", "field"]} noStyle>
                          <Select style={{ width: 100 }} placeholder="字段">
                            {Object.values(INDICATOR_CONFIG)
                              .flatMap((c) => c.fields)
                              .map((f) => (
                                <Option key={f} value={f}>
                                  {f}
                                </Option>
                              ))}
                          </Select>
                        </Form.Item>
                      </>
                    );
                  }
                  return null;
                }}
              </Form.Item>
            </Space>
          </Form.Item>
        </Card>

        {/* 描述模板 */}
        <Card title="描述模板" size="small">
          <Form.Item
            name="description_template"
            tooltip="支持变量：{entry_price:.2f} 表示入场价保留2位小数"
          >
            <Input.TextArea
              rows={2}
              placeholder="如：MA5上穿MA20，建议在MA20附近{entry_price:.2f}买入"
              maxLength={500}
            />
          </Form.Item>
        </Card>
      </Form>
    </Modal>
  );
};

export default RuleEditor;
