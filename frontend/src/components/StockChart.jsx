/**
 * 股票趋势图表组件 - 展示新浪财经静态图表 + 估值指标
 * 支持分时图、日K、周K、月K、估值详情 多种图表类型切换
 */
import { useState, useEffect } from "react";
import {
  Tabs,
  Spin,
  Empty,
  message,
  Alert,
  Card,
  Row,
  Col,
  Statistic,
  Skeleton,
  Typography,
  Divider,
} from "antd";
import {
  LineChartOutlined,
  ClockCircleOutlined,
  CalendarOutlined,
  CalendarTwoTone,
  DollarOutlined,
  WarningOutlined,
} from "@ant-design/icons";
import { stockApi } from "../services/api";

const { Text } = Typography;

/**
 * 图表类型说明配置
 */
const CHART_DESCRIPTIONS = {
  min: {
    title: "分时图",
    desc: "当日每分钟价格走势，适合观察盘中实时波动",
    icon: <ClockCircleOutlined />,
  },
  daily: {
    title: "日K线",
    desc: "每日收盘价K线图，适合短线交易分析（建议周期：1-30天）",
    icon: <LineChartOutlined />,
  },
  weekly: {
    title: "周K线",
    desc: "每周收盘价K线图，适合中线趋势分析（建议周期：1-6个月）",
    icon: <CalendarOutlined />,
  },
  monthly: {
    title: "月K线",
    desc: "每月收盘价K线图，适合长线投资分析（建议周期：6个月以上）",
    icon: <CalendarTwoTone />,
  },
  valuation: {
    title: "估值详情",
    desc: "完整估值指标分析，包括估值、盈利、成长、财务健康等维度",
    icon: <DollarOutlined />,
  },
};

/**
 * 核心估值指标配置
 */
const CORE_METRICS = [
  { key: "pe_ratio", label: "PE", subLabel: "市盈率", format: (v) => v?.toFixed(2) ?? "-" },
  { key: "pb_ratio", label: "PB", subLabel: "市净率", format: (v) => v?.toFixed(2) ?? "-" },
  { key: "roe", label: "ROE", subLabel: "净资产收益率", format: (v) => v != null ? `${(v * 100).toFixed(1)}%` : "-" },
  { key: "profit_margin", label: "利润率", subLabel: "净利润率", format: (v) => v != null ? `${(v * 100).toFixed(1)}%` : "-" },
  { key: "revenue_growth", label: "营收增", subLabel: "营收增长率", format: (v) => v != null ? `${(v * 100).toFixed(1)}%` : "-" },
];

/**
 * 趋势图展示组件
 * @param {string} symbol - 股票代码
 * @param {string} name - 股票名称
 */
const StockChart = ({ symbol, name }) => {
  const [loading, setLoading] = useState(false);
  const [chartData, setChartData] = useState(null);
  const [activeTab, setActiveTab] = useState("daily");

  // 估值数据状态
  const [valuation, setValuation] = useState(null);
  const [valuationLoading, setValuationLoading] = useState(false);
  const [valuationError, setValuationError] = useState(null);

  // 获取图表数据
  useEffect(() => {
    const fetchChartData = async () => {
      if (!symbol) return;

      setLoading(true);
      try {
        const data = await stockApi.getStockCharts(symbol);
        setChartData(data);
      } catch (error) {
        message.error("获取图表数据失败: " + error.message);
      } finally {
        setLoading(false);
      }
    };

    fetchChartData();
  }, [symbol]);

  // 并行加载估值数据
  useEffect(() => {
    const fetchValuation = async () => {
      if (!symbol) return;

      setValuationLoading(true);
      setValuationError(null);
      try {
        const data = await stockApi.getValuation(symbol);
        setValuation(data);
      } catch (error) {
        // 不抛出异常，记录错误信息
        setValuationError(error.message || "估值数据获取失败");
        setValuation(null);
      } finally {
        setValuationLoading(false);
      }
    };

    fetchValuation();
  }, [symbol]);

  // 图片展示组件
  const ChartImage = ({ src, alt }) => (
    <div style={{ textAlign: "center", padding: "10px" }}>
      <img
        src={src}
        alt={alt}
        style={{
          maxWidth: "100%",
          height: "auto",
          borderRadius: "8px",
          boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
        }}
        onError={(e) => {
          e.target.src =
            "https://via.placeholder.com/545x300?text=图表加载失败";
        }}
      />
    </div>
  );

  // 核心估值卡片
  const ValuationCard = () => {
    if (valuationLoading) {
      return (
        <Card size="small" style={{ marginBottom: 16 }}>
          <Skeleton active paragraph={{ rows: 1 }} />
        </Card>
      );
    }

    if (valuationError || !valuation) {
      return (
        <Alert
          message="估值数据获取失败"
          description={valuationError || "暂无估值数据，美股暂不支持 AKShare 估值数据"}
          type="warning"
          showIcon
          icon={<WarningOutlined />}
          style={{ marginBottom: 16 }}
        />
      );
    }

    const metrics = valuation.metrics || {};

    return (
      <Card size="small" style={{ marginBottom: 16 }}>
        <Row gutter={[8, 8]}>
          {CORE_METRICS.map((metric) => (
            <Col span={4} key={metric.key} style={{ textAlign: "center" }}>
              <Statistic
                title={
                  <span style={{ fontSize: 12, fontWeight: "bold" }}>
                    {metric.label}
                  </span>
                }
                value={metric.format(metrics[metric.key])}
                valueStyle={{ fontSize: 14 }}
              />
              <Text type="secondary" style={{ fontSize: 10 }}>
                {metric.subLabel}
              </Text>
            </Col>
          ))}
        </Row>
        <Divider style={{ margin: "8px 0" }} />
        <Text type="secondary" style={{ fontSize: 11 }}>
          数据源: {valuation.source || "-"} | 更新:{" "}
          {valuation.fetched_at
            ? new Date(valuation.fetched_at).toLocaleString("zh-CN")
            : "-"}
        </Text>
      </Card>
    );
  };

  // 估值详情内容
  const ValuationDetail = () => {
    if (valuationLoading) {
      return (
        <div style={{ padding: 24 }}>
          <Skeleton active paragraph={{ rows: 6 }} />
        </div>
      );
    }

    if (valuationError || !valuation) {
      return (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={
            <span>
              <WarningOutlined /> 暂无估值数据
              <br />
              <Text type="secondary" style={{ fontSize: 12 }}>
                {valuationError || "美股暂不支持 AKShare 估值数据"}
              </Text>
            </span>
          }
        />
      );
    }

    const metrics = valuation.metrics || {};

    // 分组定义
    const groups = [
      {
        title: "估值指标",
        items: [
          { key: "pe_ratio", label: "PE (市盈率)", format: (v) => v?.toFixed(2) },
          { key: "pb_ratio", label: "PB (市净率)", format: (v) => v?.toFixed(2) },
          { key: "ps_ratio", label: "PS (市销率)", format: (v) => v?.toFixed(2) },
          { key: "dividend_yield", label: "股息率", format: (v) => v != null ? `${(v * 100).toFixed(2)}%` : null },
        ],
      },
      {
        title: "盈利能力",
        items: [
          { key: "roe", label: "ROE (净资产收益率)", format: (v) => v != null ? `${(v * 100).toFixed(2)}%` : null },
          { key: "roa", label: "ROA (总资产收益率)", format: (v) => v != null ? `${(v * 100).toFixed(2)}%` : null },
          { key: "profit_margin", label: "净利润率", format: (v) => v != null ? `${(v * 100).toFixed(2)}%` : null },
          { key: "gross_margin", label: "毛利率", format: (v) => v != null ? `${(v * 100).toFixed(2)}%` : null },
        ],
      },
      {
        title: "成长能力",
        items: [
          { key: "revenue_growth", label: "营收增长率", format: (v) => v != null ? `${(v * 100).toFixed(2)}%` : null },
        ],
      },
      {
        title: "财务健康",
        items: [
          { key: "debt_to_equity", label: "负债权益比", format: (v) => v?.toFixed(2) },
          { key: "current_ratio", label: "流动比率", format: (v) => v?.toFixed(2) },
        ],
      },
      {
        title: "每股指标",
        items: [
          { key: "eps", label: "EPS (每股收益)", format: (v) => v?.toFixed(2) },
          { key: "book_value_per_share", label: "每股净资产", format: (v) => v?.toFixed(2) },
        ],
      },
    ];

    return (
      <div style={{ padding: "0 8px" }}>
        <Row gutter={[16, 16]}>
          {groups.map((group) => (
            <Col xs={24} sm={12} key={group.title}>
              <Card size="small" title={group.title} style={{ height: "100%" }}>
                {group.items.map((item) => {
                  const value = metrics[item.key];
                  const displayValue = value != null ? item.format(value) : "-";
                  return (
                    <div
                      key={item.key}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        padding: "4px 0",
                        borderBottom: "1px solid #f0f0f0",
                      }}
                    >
                      <Text type="secondary">{item.label}</Text>
                      <Text strong>{displayValue}</Text>
                    </div>
                  );
                })}
              </Card>
            </Col>
          ))}
        </Row>
        <Divider style={{ margin: "16px 0" }} />
        <Text type="secondary" style={{ fontSize: 11 }}>
          数据来源: {valuation.source || "-"} | 获取时间:{" "}
          {valuation.fetched_at
            ? new Date(valuation.fetched_at).toLocaleString("zh-CN")
            : "-"}
        </Text>
      </div>
    );
  };

  // 图表标签页配置
  const tabItems = Object.entries(CHART_DESCRIPTIONS).map(([key, config]) => ({
    key,
    label: (
      <span>
        {config.icon} {config.title}
      </span>
    ),
    children:
      key === "valuation" ? (
        <ValuationDetail />
      ) : (
        <div>
          {/* 图表说明 */}
          <Alert
            message={config.desc}
            type="info"
            showIcon
            style={{ marginBottom: 12, fontSize: 12 }}
          />
          {/* 图表图片 */}
          {chartData?.[key] ? (
            <ChartImage src={chartData[key]} alt={config.title} />
          ) : (
            <Empty description="暂无数据" />
          )}
        </div>
      ),
  }));

  return (
    <Spin spinning={loading}>
      <div style={{ minHeight: 400 }}>
        {/* 股票信息标题 */}
        <div
          style={{
            marginBottom: 16,
            padding: "12px 16px",
            background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
            borderRadius: 8,
            color: "#fff",
          }}
        >
          <div style={{ fontSize: 16, fontWeight: "bold" }}>{name}</div>
          <div style={{ fontSize: 12, opacity: 0.9 }}>{symbol}</div>
        </div>

        {/* 核心估值卡片 */}
        <ValuationCard />

        {/* 图表切换标签页 */}
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={tabItems}
          size="large"
          tabBarStyle={{ marginBottom: 16 }}
        />

        {/* 底部提示 */}
        <div
          style={{
            textAlign: "center",
            color: "#999",
            fontSize: 11,
            marginTop: 8,
          }}
        >
          图表数据来源：新浪财经 | 建议在交易时间内查看最新数据
        </div>
      </div>
    </Spin>
  );
};

export default StockChart;
