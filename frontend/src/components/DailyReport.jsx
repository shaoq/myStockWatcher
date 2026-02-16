/**
 * 每日报告页面 - 展示股票指标变化和趋势，支持查看历史报告
 */
import { useState, useEffect } from "react";
import {
  Card,
  Row,
  Col,
  Statistic,
  List,
  Tag,
  Button,
  Space,
  message,
  Spin,
  Empty,
  Typography,
  Divider,
  DatePicker,
} from "antd";
import {
  RiseOutlined,
  FallOutlined,
  SyncOutlined,
  CalendarOutlined,
  StockOutlined,
  LeftOutlined,
  RightOutlined,
} from "@ant-design/icons";
import dayjs from "dayjs";
import { stockApi } from "../services/api";

const { Title, Text } = Typography;

const DailyReport = () => {
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [snapshotStatus, setSnapshotStatus] = useState(null);
  const [report, setReport] = useState(null);
  const [trendData, setTrendData] = useState(null);
  const [availableDates, setAvailableDates] = useState([]);
  const [selectedDate, setSelectedDate] = useState(null);
  const [prevDate, setPrevDate] = useState(null);
  const [nextDate, setNextDate] = useState(null);

  // 加载快照日期列表
  const loadSnapshotDates = async () => {
    try {
      const data = await stockApi.getSnapshotDates();
      const dates = data.dates.map((d) => dayjs(d));
      setAvailableDates(dates);
      setPrevDate(data.prev_date ? dayjs(data.prev_date) : null);
      setNextDate(data.next_date ? dayjs(data.next_date) : null);
      return dates;
    } catch (error) {
      console.error("加载快照日期失败:", error);
      return [];
    }
  };

  // 加载快照状态
  const loadSnapshotStatus = async () => {
    try {
      const data = await stockApi.checkTodaySnapshots();
      setSnapshotStatus(data);
      return data;
    } catch (error) {
      console.error("检查快照状态失败:", error);
      return null;
    }
  };

  // 加载报告数据
  const loadReport = async (targetDate = null) => {
    setLoading(true);
    try {
      const dateStr = targetDate ? targetDate.format("YYYY-MM-DD") : null;
      const [reportData, trend] = await Promise.all([
        stockApi.getDailyReport(dateStr),
        stockApi.getTrendData(7),
      ]);
      setReport(reportData);
      setTrendData(trend.data);

      // 更新相邻日期
      if (targetDate) {
        const currentDate = targetDate.format("YYYY-MM-DD");
        const currentIdx = availableDates.findIndex(
          (d) => d.format("YYYY-MM-DD") === currentDate
        );
        setPrevDate(
          currentIdx > 0 ? availableDates[currentIdx - 1] : null
        );
        setNextDate(
          currentIdx < availableDates.length - 1
            ? availableDates[currentIdx + 1]
            : null
        );
      }
    } catch (error) {
      message.error("加载报告失败: " + error.message);
    } finally {
      setLoading(false);
    }
  };

  // 生成快照
  const handleGenerateSnapshots = async () => {
    setGenerating(true);
    try {
      const result = await stockApi.generateSnapshots();
      message.success(result.message);
      await loadSnapshotStatus();
      await loadSnapshotDates();
      await loadReport();
    } catch (error) {
      message.error("生成快照失败: " + error.message);
    } finally {
      setGenerating(false);
    }
  };

  // 日期选择变化
  const handleDateChange = (date) => {
    if (!date) return;
    setSelectedDate(date);
    loadReport(date);
  };

  // 导航到前一日期
  const handlePrevDate = () => {
    if (prevDate) {
      setSelectedDate(prevDate);
      loadReport(prevDate);
    }
  };

  // 导航到后一日期
  const handleNextDate = () => {
    if (nextDate) {
      setSelectedDate(nextDate);
      loadReport(nextDate);
    }
  };

  // 禁用没有快照的日期
  const disabledDate = (current) => {
    if (!current) return true;
    const dateStr = current.format("YYYY-MM-DD");
    return !availableDates.some((d) => d.format("YYYY-MM-DD") === dateStr);
  };

  useEffect(() => {
    const init = async () => {
      const dates = await loadSnapshotDates();
      const status = await loadSnapshotStatus();
      if (status && status.has_snapshots) {
        await loadReport();
      }
    };
    init();
  }, []);

  // 渲染变化项
  const renderChangeItem = (item, type) => {
    const isRise = type === "reached";
    const color = isRise ? "success" : "error";
    const icon = isRise ? <RiseOutlined /> : <FallOutlined />;

    return (
      <List.Item>
        <List.Item.Meta
          avatar={
            <Tag color={color} icon={icon}>
              {item.ma_type}
            </Tag>
          }
          title={
            <Space>
              <span style={{ fontWeight: "bold" }}>{item.symbol}</span>
              <span style={{ color: "#8c8c8c" }}>{item.name}</span>
            </Space>
          }
          description={
            <Space split={<Divider type="vertical" />}>
              <span>现价: ¥{item.current_price?.toFixed(2)}</span>
              <span>均线: ¥{item.ma_price?.toFixed(2)}</span>
              <span style={{ color: isRise ? "#52c41a" : "#ff4d4f" }}>
                偏离: {item.price_difference_percent > 0 ? "+" : ""}
                {item.price_difference_percent?.toFixed(2)}%
              </span>
            </Space>
          }
        />
      </List.Item>
    );
  };

  // 简单的趋势图（使用 ASCII 艺术风格）
  const renderTrendChart = () => {
    if (!trendData || trendData.length === 0) {
      return <Empty description="暂无趋势数据" />;
    }

    const maxCount = Math.max(...trendData.map((d) => d.reached_count), 1);
    const chartHeight = 8;

    return (
      <div
        style={{
          background: "#fafafa",
          padding: "16px",
          borderRadius: "8px",
          overflow: "auto",
        }}
      >
        {/* Y轴刻度 */}
        <div style={{ display: "flex", marginBottom: "8px" }}>
          <div
            style={{
              width: "40px",
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
              height: `${chartHeight * 10}px`,
              color: "#8c8c8c",
              fontSize: "12px",
            }}
          >
            <span>{maxCount}</span>
            <span>{Math.round(maxCount / 2)}</span>
            <span>0</span>
          </div>

          {/* 柱状图区域 */}
          <div
            style={{
              display: "flex",
              gap: "8px",
              flex: 1,
              alignItems: "flex-end",
            }}
          >
            {trendData.map((item, index) => {
              const heightPercent = (item.reached_count / maxCount) * 100;
              return (
                <div
                  key={index}
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    flex: 1,
                  }}
                >
                  <div
                    style={{
                      width: "100%",
                      maxWidth: "40px",
                      height: `${chartHeight * 10}px`,
                      display: "flex",
                      alignItems: "flex-end",
                    }}
                  >
                    <div
                      style={{
                        width: "100%",
                        height: `${heightPercent}%`,
                        background:
                          index === trendData.length - 1
                            ? "#1890ff"
                            : "#91d5ff",
                        borderRadius: "4px 4px 0 0",
                        transition: "height 0.3s",
                        display: "flex",
                        alignItems: "flex-start",
                        justifyContent: "center",
                        color: "#fff",
                        fontSize: "12px",
                        fontWeight: "bold",
                        paddingTop: "4px",
                      }}
                    >
                      {item.reached_count}
                    </div>
                  </div>
                  <div
                    style={{
                      fontSize: "11px",
                      color: "#8c8c8c",
                      marginTop: "4px",
                    }}
                  >
                    {item.date}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* 达标率 */}
        <div style={{ marginTop: "16px", textAlign: "center" }}>
          <Text type="secondary">
            近 {trendData.length} 日达标趋势 · 达标率{" "}
            {trendData[trendData.length - 1]?.reached_rate || 0}%
          </Text>
        </div>
      </div>
    );
  };

  // 没有快照时的提示
  if (!loading && snapshotStatus && !snapshotStatus.has_snapshots) {
    return (
      <div style={{ padding: "24px" }}>
        <Card>
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
              <Space direction="vertical" size="large">
                <div>
                  <CalendarOutlined
                    style={{ fontSize: "48px", color: "#1890ff" }}
                  />
                </div>
                <Title level={4}>今日还没有生成快照</Title>
                <Text type="secondary">
                  快照用于保存股票的当前状态，生成后可以查看每日报告和趋势分析
                </Text>
                <Button
                  type="primary"
                  size="large"
                  icon={<SyncOutlined spin={generating} />}
                  loading={generating}
                  onClick={handleGenerateSnapshots}
                >
                  生成今日快照
                </Button>
              </Space>
            }
          />
        </Card>
      </div>
    );
  }

  return (
    <div style={{ padding: "24px" }}>
      <Card
        title={
          <Space>
            <StockOutlined />
            <span>每日报告</span>
            {report && <Tag color="blue">{report.report_date}</Tag>}
          </Space>
        }
        extra={
          <Space>
            {/* 日期导航 */}
            <Space.Compact>
              <Button
                icon={<LeftOutlined />}
                onClick={handlePrevDate}
                disabled={!prevDate}
              />
              <DatePicker
                value={selectedDate || dayjs()}
                onChange={handleDateChange}
                disabledDate={disabledDate}
                allowClear={false}
                style={{ width: 150 }}
                format="YYYY-MM-DD"
              />
              <Button
                icon={<RightOutlined />}
                onClick={handleNextDate}
                disabled={!nextDate}
              />
            </Space.Compact>
            <Button
              icon={<SyncOutlined spin={generating} />}
              loading={generating}
              onClick={handleGenerateSnapshots}
            >
              刷新快照
            </Button>
          </Space>
        }
      >
        <Spin spinning={loading}>
          {report ? (
            <>
              {/* 概览卡片 */}
              <Row gutter={16} style={{ marginBottom: 24 }}>
                <Col xs={12} sm={6}>
                  <Card>
                    <Statistic
                      title="监控总数"
                      value={report.summary.total_stocks}
                      suffix="只"
                    />
                  </Card>
                </Col>
                <Col xs={12} sm={6}>
                  <Card>
                    <Statistic
                      title="今日达标"
                      value={report.summary.reached_count}
                      valueStyle={{ color: "#52c41a" }}
                      suffix={
                        <span style={{ fontSize: "14px", color: "#8c8c8c" }}>
                          / {report.summary.total_stocks}
                        </span>
                      }
                    />
                  </Card>
                </Col>
                <Col xs={12} sm={6}>
                  <Card>
                    <Statistic
                      title="新增达标"
                      value={report.summary.newly_reached}
                      valueStyle={{ color: "#1890ff" }}
                      prefix={<RiseOutlined />}
                    />
                  </Card>
                </Col>
                <Col xs={12} sm={6}>
                  <Card>
                    <Statistic
                      title="跌破均线"
                      value={report.summary.newly_below}
                      valueStyle={{ color: "#ff4d4f" }}
                      prefix={<FallOutlined />}
                    />
                  </Card>
                </Col>
              </Row>

              {/* 达标率 */}
              <Card style={{ marginBottom: 24 }}>
                <Row gutter={16} align="middle">
                  <Col span={12}>
                    <Statistic
                      title="达标率"
                      value={report.summary.reached_rate}
                      precision={1}
                      suffix="%"
                    />
                  </Col>
                  <Col span={12}>
                    {report.has_yesterday ? (
                      <Statistic
                        title="较昨日变化"
                        value={Math.abs(report.summary.reached_rate_change)}
                        precision={1}
                        suffix="%"
                        valueStyle={{
                          color:
                            report.summary.reached_rate_change >= 0
                              ? "#52c41a"
                              : "#ff4d4f",
                        }}
                        prefix={
                          report.summary.reached_rate_change >= 0 ? (
                            <RiseOutlined />
                          ) : (
                            <FallOutlined />
                          )
                        }
                      />
                    ) : (
                      <Text type="secondary">暂无昨日数据对比</Text>
                    )}
                  </Col>
                </Row>
              </Card>

              {/* 变化列表 */}
              <Row gutter={16} style={{ marginBottom: 24 }}>
                <Col xs={24} lg={12}>
                  <Card
                    title={
                      <Space>
                        <RiseOutlined style={{ color: "#52c41a" }} />
                        <span>新增达标</span>
                        <Tag color="success">
                          {report.newly_reached.length}
                        </Tag>
                      </Space>
                    }
                    size="small"
                  >
                    {report.newly_reached.length > 0 ? (
                      <List
                        dataSource={report.newly_reached}
                        renderItem={(item) =>
                          renderChangeItem(item, "reached")
                        }
                        size="small"
                      />
                    ) : (
                      <Empty
                        image={Empty.PRESENTED_IMAGE_SIMPLE}
                        description="无新增达标"
                      />
                    )}
                  </Card>
                </Col>
                <Col xs={24} lg={12}>
                  <Card
                    title={
                      <Space>
                        <FallOutlined style={{ color: "#ff4d4f" }} />
                        <span>跌破均线</span>
                        <Tag color="error">{report.newly_below.length}</Tag>
                      </Space>
                    }
                    size="small"
                  >
                    {report.newly_below.length > 0 ? (
                      <List
                        dataSource={report.newly_below}
                        renderItem={(item) => renderChangeItem(item, "below")}
                        size="small"
                      />
                    ) : (
                      <Empty
                        image={Empty.PRESENTED_IMAGE_SIMPLE}
                        description="无跌破均线"
                      />
                    )}
                  </Card>
                </Col>
              </Row>

              {/* 趋势图表 */}
              <Card title="近 7 日趋势">{renderTrendChart()}</Card>
            </>
          ) : (
            <Empty description="加载中..." />
          )}
        </Spin>
      </Card>
    </div>
  );
};

export default DailyReport;
