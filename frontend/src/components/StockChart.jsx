/**
 * 股票趋势图表组件 - 展示新浪财经静态图表
 * 支持分时图、日K、周K、月K 多种图表类型切换
 */
import { useState, useEffect } from "react";
import { Tabs, Spin, Empty, message, Alert } from "antd";
import {
  LineChartOutlined,
  ClockCircleOutlined,
  CalendarOutlined,
  CalendarTwoTone,
} from "@ant-design/icons";
import { stockApi } from "../services/api";

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
};

/**
 * 趋势图展示组件
 * @param {string} symbol - 股票代码
 * @param {string} name - 股票名称
 */
const StockChart = ({ symbol, name }) => {
  const [loading, setLoading] = useState(false);
  const [chartData, setChartData] = useState(null);
  const [activeTab, setActiveTab] = useState("daily");

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

  // 图表标签页配置
  const tabItems = Object.entries(CHART_DESCRIPTIONS).map(([key, config]) => ({
    key,
    label: (
      <span>
        {config.icon} {config.title}
      </span>
    ),
    children: (
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
