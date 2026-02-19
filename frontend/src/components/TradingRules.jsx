/**
 * 交易规则配置页面
 *
 * 功能：
 * - 按买入/卖出分组展示规则列表
 * - 支持启用/禁用规则
 * - 支持编辑/删除规则
 * - 批量重算信号
 */
import React, { useState, useEffect } from "react";
import {
  Card,
  Table,
  Button,
  Switch,
  Space,
  Tag,
  Modal,
  message,
  Popconfirm,
  Tabs,
  Tooltip,
  Badge,
} from "antd";
import {
  PlusOutlined,
  ReloadOutlined,
  EditOutlined,
  DeleteOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";
import { ruleApi } from "../services/api";
import RuleEditor from "./RuleEditor";

const TradingRules = () => {
  const [loading, setLoading] = useState(false);
  const [rules, setRules] = useState([]);
  const [editorVisible, setEditorVisible] = useState(false);
  const [editingRule, setEditingRule] = useState(null);
  const [recalculating, setRecalculating] = useState(false);

  // 加载规则列表
  const loadRules = async () => {
    setLoading(true);
    try {
      const data = await ruleApi.getRules();
      setRules(data);
    } catch (error) {
      message.error(`加载规则失败: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRules();
  }, []);

  // 切换规则启用状态
  const handleToggleEnabled = async (rule) => {
    try {
      await ruleApi.updateRule(rule.id, { enabled: !rule.enabled });
      message.success(`规则已${rule.enabled ? "禁用" : "启用"}`);
      loadRules();
    } catch (error) {
      message.error(`操作失败: ${error.message}`);
    }
  };

  // 删除规则
  const handleDelete = async (ruleId) => {
    try {
      await ruleApi.deleteRule(ruleId);
      message.success("规则已删除");
      loadRules();
    } catch (error) {
      message.error(`删除失败: ${error.message}`);
    }
  };

  // 打开编辑弹窗
  const handleEdit = (rule) => {
    setEditingRule(rule);
    setEditorVisible(true);
  };

  // 打开新建弹窗
  const handleCreate = (ruleType) => {
    setEditingRule({ rule_type: ruleType });
    setEditorVisible(true);
  };

  // 保存规则后的回调
  const handleEditorClose = (needRecalculate) => {
    setEditorVisible(false);
    setEditingRule(null);
    loadRules();

    if (needRecalculate) {
      Modal.confirm({
        title: "规则已保存",
        content: "是否立即重新计算所有股票的信号？",
        okText: "立即计算",
        cancelText: "稍后再说",
        onOk: () => handleRecalculate(),
      });
    }
  };

  // 批量重算信号
  const handleRecalculate = async () => {
    setRecalculating(true);
    try {
      const result = await ruleApi.recalculateSignals();
      message.success(
        `重算完成：成功 ${result.success_count} 只，失败 ${result.error_count} 只`
      );
    } catch (error) {
      message.error(`重算失败: ${error.message}`);
    } finally {
      setRecalculating(false);
    }
  };

  // 表格列定义
  const columns = [
    {
      title: "规则名称",
      dataIndex: "name",
      key: "name",
      width: 180,
    },
    {
      title: "优先级",
      dataIndex: "priority",
      key: "priority",
      width: 80,
      sorter: (a, b) => a.priority - b.priority,
    },
    {
      title: "强度",
      dataIndex: "strength",
      key: "strength",
      width: 100,
      render: (strength) => (
        <Space>
          {[1, 2, 3, 4, 5].map((i) => (
            <span key={i} style={{ color: i <= strength ? "#faad14" : "#d9d9d9" }}>
              ★
            </span>
          ))}
        </Space>
      ),
    },
    {
      title: "状态",
      dataIndex: "enabled",
      key: "enabled",
      width: 80,
      render: (enabled, record) => (
        <Switch
          checked={enabled}
          onChange={() => handleToggleEnabled(record)}
          checkedChildren="启用"
          unCheckedChildren="禁用"
        />
      ),
    },
    {
      title: "操作",
      key: "action",
      width: 120,
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定删除此规则吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // 按类型过滤规则
  const buyRules = rules.filter((r) => r.rule_type === "buy");
  const sellRules = rules.filter((r) => r.rule_type === "sell");

  // Tab 内容
  const tabItems = [
    {
      key: "buy",
      label: (
        <span>
          买入规则 <Badge count={buyRules.length} style={{ marginLeft: 8 }} />
        </span>
      ),
      children: (
        <div>
          <div style={{ marginBottom: 16 }}>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => handleCreate("buy")}
            >
              新增买入规则
            </Button>
          </div>
          <Table
            columns={columns}
            dataSource={buyRules}
            rowKey="id"
            loading={loading}
            pagination={false}
            size="small"
          />
        </div>
      ),
    },
    {
      key: "sell",
      label: (
        <span>
          卖出规则 <Badge count={sellRules.length} style={{ marginLeft: 8 }} />
        </span>
      ),
      children: (
        <div>
          <div style={{ marginBottom: 16 }}>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => handleCreate("sell")}
            >
              新增卖出规则
            </Button>
          </div>
          <Table
            columns={columns}
            dataSource={sellRules}
            rowKey="id"
            loading={loading}
            pagination={false}
            size="small"
          />
        </div>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      <Card
        title="买卖规则配置"
        extra={
          <Tooltip title="使用当前启用的规则重新计算所有股票信号">
            <Button
              type="primary"
              icon={<ThunderboltOutlined />}
              loading={recalculating}
              onClick={handleRecalculate}
            >
              批量重算信号
            </Button>
          </Tooltip>
        }
      >
        <Tabs items={tabItems} />
      </Card>

      {/* 规则编辑弹窗 */}
      <RuleEditor
        visible={editorVisible}
        rule={editingRule}
        onClose={handleEditorClose}
      />
    </div>
  );
};

export default TradingRules;
