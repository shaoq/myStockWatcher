/**
 * 每日报告页面 - 展示股票指标变化和趋势，支持查看历史报告和交易日判断
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
  Alert,
  Modal,
} from "antd";
import {
  RiseOutlined,
  FallOutlined,
  SyncOutlined,
  CalendarOutlined,
  StockOutlined,
  LeftOutlined,
  RightOutlined,
  ClockCircleOutlined,
  WarningOutlined,
} from "@ant-design/icons";
import dayjs from "dayjs";
import { stockApi } from "../services/api";

const { Title, Text } = Typography;

const DailyReport = () => {
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [checkingTradingDay, setCheckingTradingDay] = useState(false); // 交易日检查状态
  const [snapshotStatus, setSnapshotStatus] = useState(null);
  const [report, setReport] = useState(null);
  const [trendData, setTrendData] = useState(null);
  const [availableDates, setAvailableDates] = useState([]);
  const [selectedDate, setSelectedDate] = useState(null);
  const [prevDate, setPrevDate] = useState(null);
  const [nextDate, setNextDate] = useState(null);
  const [tradingDayInfo, setTradingDayInfo] = useState(null); // 交易日信息
  const [isNonTradingDay, setIsNonTradingDay] = useState(false); // 是否为非交易日

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

  // 检查交易日状态
  const checkTradingDayStatus = async (targetDate = null) => {
    setCheckingTradingDay(true);
    try {
      const dateStr = targetDate ? targetDate.format("YYYY-MM-DD") : null;
      const data = await stockApi.checkTradingDay(dateStr);
      setTradingDayInfo(data);
      setIsNonTradingDay(!data.is_trading_day);
      return data;
    } catch (error) {
      console.error("检查交易日失败:", error);
      message.error("无法获取交易日信息，请稍后重试");
      return null;
    } finally {
      setCheckingTradingDay(false);
    }
  };

  // 加载报告数据
  const loadReport = async (targetDate = null) => {
    setLoading(true);
    setIsNonTradingDay(false);

    try {
      // 先检查是否为交易日
      const tradingInfo = await checkTradingDayStatus(targetDate);
      if (tradingInfo && !tradingInfo.is_trading_day) {
        setIsNonTradingDay(true);
        setReport(null);
        setLoading(false);
        return;
      }

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
          (d) => d.format("YYYY-MM-DD") === currentDate,
        );
        setPrevDate(currentIdx > 0 ? availableDates[currentIdx - 1] : null);
        setNextDate(
          currentIdx < availableDates.length - 1
            ? availableDates[currentIdx + 1]
            : null,
        );
      }
    } catch (error) {
      // 处理非交易日错误
      if (error.detail && error.detail.is_trading_day === false) {
        setIsNonTradingDay(true);
        setTradingDayInfo(error.detail);
        setReport(null);
      } else {
        message.error("加载报告失败: " + error.message);
      }
    } finally {
      setLoading(false);
    }
  };

  // 生成快照（支持指定日期）
  const handleGenerateSnapshots = async (targetDate = null) => {
    setGenerating(true);
    try {
      const dateStr = targetDate ? targetDate.format("YYYY-MM-DD") : null;
      const result = await stockApi.generateSnapshots(dateStr);
      message.success(result.message);
      await loadSnapshotStatus();
      await loadSnapshotDates();
      await loadReport(targetDate);
    } catch (error) {
      // 处理非交易日错误
      if (error.detail && error.detail.is_trading_day === false) {
        message.warning(`该日期为非交易日（${error.detail.reason}）`);
      } else {
        message.error("生成快照失败: " + error.message);
      }
    } finally {
      setGenerating(false);
    }
  };

  // 日期选择变化
  const handleDateChange = async (date) => {
    if (!date) return;
    setSelectedDate(date);

    // 检查是否为交易日
    const tradingInfo = await checkTradingDayStatus(date);
    if (tradingInfo && !tradingInfo.is_trading_day) {
      setIsNonTradingDay(true);
      setReport(null);
      return;
    }

    // 检查该日期是否有快照
    const dateStr = date.format("YYYY-MM-DD");
    const hasSnapshot = availableDates.some(
      (d) => d.format("YYYY-MM-DD") === dateStr,
    );

    if (!hasSnapshot) {
      // 无快照，弹出确认对话框询问是否生成
      Modal.confirm({
        title: "该日期暂无分析报告",
        content: `是否为 ${dateStr} 生成分析报告？`,
        okText: "确认生成",
        cancelText: "取消",
        onOk: () => handleGenerateSnapshots(date),
        onCancel: () => {
          // 用户取消，保持在当前视图
          setSelectedDate(null);
        },
      });
    } else {
      // 有快照，直接加载报告
      loadReport(date);
    }
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

  // 禁用未来日期（只能选择今天及之前的日期）
  const disabledDate = (current) => {
    if (!current) return true;
    // 禁用今天之后的日期
    return current && current.isAfter(dayjs().endOf("day"));
  };

  useEffect(() => {
    const init = async () => {
      const dates = await loadSnapshotDates();
      const status = await loadSnapshotStatus();

      // 检查今天是否为交易日
      const tradingInfo = await checkTradingDayStatus();

      if (tradingInfo && !tradingInfo.is_trading_day) {
        // 非交易日，不自动加载报告
        setIsNonTradingDay(true);
      } else if (status && status.has_snapshots) {
        // 交易日且已有快照，加载报告
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

  // 没有快照时的提示（区分交易日和非交易日）
  if (!loading && snapshotStatus && !snapshotStatus.has_snapshots) {
    return (
      <div style={{ padding: "24px" }}>
        <Card>
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description={
              <Space direction="vertical" size="large">
                <div>
                  {isNonTradingDay ? (
                    <ClockCircleOutlined
                      style={{ fontSize: "48px", color: "#faad14" }}
                    />
                  ) : (
                    <CalendarOutlined
                      style={{ fontSize: "48px", color: "#1890ff" }}
                    />
                  )}
                </div>
                {isNonTradingDay ? (
                  <>
                    <Title level={4}>今日为非交易日</Title>
                    <Text type="secondary">
                      {tradingDayInfo?.reason === "周末"
                        ? "股票市场周末休市"
                        : tradingDayInfo?.reason === "节假日"
                          ? "股票市场节假日休市"
                          : "该日期市场休市"}
                    </Text>
                    <Text type="secondary">您可以选择历史交易日查看报告</Text>
                  </>
                ) : (
                  <>
                    <Title level={4}>今日还没有生成快照</Title>
                    <Text type="secondary">
                      快照用于保存股票的当前状态，生成后可以查看每日报告和趋势分析
                    </Text>
                    <Button
                      type="primary"
                      size="large"
                      icon={<SyncOutlined spin={generating} />}
                      loading={generating}
                      onClick={() => handleGenerateSnapshots()}
                    >
                      生成今日快照
                    </Button>
                  </>
                )}
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
            {checkingTradingDay && (
              <Tag color="processing" icon={<SyncOutlined spin />}>
                检查中...
              </Tag>
            )}
            {!checkingTradingDay && tradingDayInfo && (
              <Tag
                color={tradingDayInfo.is_trading_day ? "success" : "warning"}
                icon={
                  tradingDayInfo.is_trading_day ? null : <ClockCircleOutlined />
                }
              >
                {tradingDayInfo.is_trading_day ? "交易日" : "休市"}
              </Tag>
            )}
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
              onClick={() => handleGenerateSnapshots(selectedDate)}
              disabled={isNonTradingDay}
            >
              {selectedDate && !selectedDate.isSame(dayjs(), "day")
                ? "生成历史快照"
                : "刷新快照"}
            </Button>
          </Space>
        }
      >
        <Spin spinning={loading}>
          {/* 非交易日提示 */}
          {isNonTradingDay && (
            <Alert
              message="该日期为非交易日"
              description={
                <Space direction="vertical">
                  <span>原因：{tradingDayInfo?.reason || "市场休市"}</span>
                  <span>您可以选择历史交易日查看或生成报告</span>
                </Space>
              }
              type="warning"
              icon={<WarningOutlined />}
              showIcon
              style={{ marginBottom: 24 }}
            />
          )}
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
                        <Tag color="success">{report.newly_reached.length}</Tag>
                      </Space>
                    }
                    size="small"
                  >
                    {report.newly_reached.length > 0 ? (
                      <List
                        dataSource={report.newly_reached}
                        renderItem={(item) => renderChangeItem(item, "reached")}
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
