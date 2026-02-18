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
  Table,
  Pagination,
  Collapse,
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
const { Panel } = Collapse;

// ============ MA 分组辅助函数 ============

/**
 * 提取 MA 类型中的数字（用于排序）
 * @param {string} maType - MA 类型，如 "MA5", "MA10"
 * @returns {number} - 数字值
 */
const getMANumber = (maType) => {
  const match = maType?.match(/\d+/);
  return match ? parseInt(match[0], 10) : 0;
};

/**
 * 将扁平数组按 ma_type 分组
 * @param {Array} items - 扁平数组
 * @returns {Object} - { "MA5": [...], "MA10": [...] }
 */
const groupByMA = (items) => {
  if (!items || items.length === 0) return {};
  return items.reduce((acc, item) => {
    const maType = item.ma_type || "Unknown";
    if (!acc[maType]) {
      acc[maType] = [];
    }
    acc[maType].push(item);
    return acc;
  }, {});
};

/**
 * 按偏离度降序排序组内项目
 * @param {Array} items - 项目数组
 * @returns {Array} - 排序后的数组
 */
const sortItemsByDeviation = (items) => {
  if (!items) return [];
  return [...items].sort((a, b) => {
    const devA = Math.abs(a.price_difference_percent || 0);
    const devB = Math.abs(b.price_difference_percent || 0);
    return devB - devA; // 降序
  });
};

/**
 * 过滤空分组并按 MA 数字升序排序
 * @param {Object} groups - 分组对象
 * @returns {Array} - 排序后的分组键数组
 */
const getSortedGroupKeys = (groups) => {
  return Object.keys(groups)
    .filter((key) => groups[key] && groups[key].length > 0) // 过滤空分组
    .sort((a, b) => getMANumber(a) - getMANumber(b)); // 按数字升序
};

const DailyReport = () => {
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [checkingTradingDay, setCheckingTradingDay] = useState(false); // 交易日检查状态
  const [snapshotStatus, setSnapshotStatus] = useState(null);
  const [report, setReport] = useState(null);
  const [trendData, setTrendData] = useState(null);
  const [availableDates, setAvailableDates] = useState([]);
  const [tradingDays, setTradingDays] = useState([]); // 当前月份的交易日列表
  const [selectedDate, setSelectedDate] = useState(null);
  const [prevDate, setPrevDate] = useState(null);
  const [nextDate, setNextDate] = useState(null);
  const [tradingDayInfo, setTradingDayInfo] = useState(null); // 交易日信息
  const [isNonTradingDay, setIsNonTradingDay] = useState(false); // 是否为非交易日

  // 达标个股分页状态
  const [reachedPage, setReachedPage] = useState(1);
  const [reachedPageSize, setReachedPageSize] = useState(10);
  const [reachedTotal, setReachedTotal] = useState(0);

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

  // 加载指定月份的交易日数据
  const loadTradingDays = async (year, month) => {
    try {
      const data = await stockApi.getMonthlyTradingDays(year, month);
      setTradingDays(data.trading_days || []);
      return data.trading_days || [];
    } catch (error) {
      console.error("加载交易日数据失败:", error);
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
  const loadReport = async (targetDate = null, page = 1, pageSize = 10) => {
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
        stockApi.getDailyReport(dateStr, page, pageSize),
        stockApi.getTrendData(7),
      ]);
      setReport(reportData);
      setTrendData(trend.data);
      setReachedTotal(reportData.total_reached || 0);

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
      setReachedPage(1); // 重置页码
      loadReport(date, 1, reachedPageSize);
    }
  };

  // 导航到前一日期
  const handlePrevDate = () => {
    if (prevDate) {
      setSelectedDate(prevDate);
      setReachedPage(1); // 重置页码
      loadReport(prevDate, 1, reachedPageSize);
    }
  };

  // 导航到后一日期
  const handleNextDate = () => {
    if (nextDate) {
      setSelectedDate(nextDate);
      setReachedPage(1); // 重置页码
      loadReport(nextDate, 1, reachedPageSize);
    }
  };

  // 达标个股分页变化
  const handleReachedPageChange = async (page, pageSize) => {
    setReachedPage(page);
    setReachedPageSize(pageSize);
    const dateStr = selectedDate ? selectedDate.format("YYYY-MM-DD") : null;
    try {
      const reportData = await stockApi.getDailyReport(dateStr, page, pageSize);
      setReport(reportData);
      setReachedTotal(reportData.total_reached || 0);
    } catch (error) {
      message.error("加载数据失败: " + error.message);
    }
  };

  // 禁用未来日期（只能选择今天及之前的日期）
  const disabledDate = (current) => {
    if (!current) return true;
    // 禁用今天之后的日期
    return current && current.isAfter(dayjs().endOf("day"));
  };

  // 自定义日期单元格渲染：为有报告的交易日添加绿色小圆点
  const renderDateCell = (current, info) => {
    if (info.type !== "date") return info.originNode;

    const dateStr = current.format("YYYY-MM-DD");

    // 检查是否为交易日
    const isTradingDay = tradingDays.includes(dateStr);
    if (!isTradingDay) {
      return info.originNode;
    }

    // 检查当前日期是否有报告
    const hasReport = availableDates.some(
      (d) => d.format("YYYY-MM-DD") === dateStr,
    );

    if (hasReport) {
      return (
        <div className="ant-picker-cell-inner" style={{ position: "relative" }}>
          {current.date()}
          <span
            style={{
              position: "absolute",
              top: 2,
              right: 2,
              width: 6,
              height: 6,
              borderRadius: "50%",
              background: "#52c41a",
            }}
          />
        </div>
      );
    }

    return info.originNode;
  };

  // 日历面板切换时加载对应月份的交易日数据
  const handlePanelChange = (date, mode) => {
    if (mode === "date") {
      loadTradingDays(date.year(), date.month() + 1);
    }
  };

  useEffect(() => {
    const init = async () => {
      const dates = await loadSnapshotDates();
      const status = await loadSnapshotStatus();

      // 加载当前月份的交易日数据
      const today = dayjs();
      await loadTradingDays(today.year(), today.month() + 1);

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

  // 渲染 MA 分组折叠面板
  const renderMACollapsePanel = (items, type) => {
    const isRise = type === "reached";
    const grouped = groupByMA(items);
    const sortedKeys = getSortedGroupKeys(grouped);

    if (sortedKeys.length === 0) {
      return (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={isRise ? "无新增达标" : "无跌破均线"}
        />
      );
    }

    return (
      <Collapse defaultActiveKey={sortedKeys} ghost expandIconPosition="end">
        {sortedKeys.map((maType) => {
          const groupItems = sortItemsByDeviation(grouped[maType]);
          return (
            <Panel
              key={maType}
              header={
                <Space>
                  <Tag color={isRise ? "success" : "error"}>{maType}</Tag>
                  <Text strong>{maType}</Text>
                  <Text type="secondary">({groupItems.length}只)</Text>
                </Space>
              }
            >
              <List
                dataSource={groupItems}
                renderItem={(item) => renderChangeItem(item, type)}
                size="small"
              />
            </Panel>
          );
        })}
      </Collapse>
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
                onPanelChange={handlePanelChange}
                disabledDate={disabledDate}
                cellRender={renderDateCell}
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
                    {renderMACollapsePanel(report.newly_reached, "reached")}
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
                    {renderMACollapsePanel(report.newly_below, "below")}
                  </Card>
                </Col>
              </Row>

              {/* 今日达标个股 */}
              <Card
                title={
                  <Space>
                    <span>今日达标个股</span>
                    <Tag color="success">{reachedTotal}只</Tag>
                  </Space>
                }
                style={{ marginBottom: 24 }}
              >
                {report.reached_stocks && report.reached_stocks.length > 0 ? (
                  <>
                    <Table
                      dataSource={report.reached_stocks}
                      rowKey="stock_id"
                      pagination={false}
                      size="small"
                      columns={[
                        {
                          title: "代码",
                          dataIndex: "symbol",
                          key: "symbol",
                          width: 100,
                          render: (text) => (
                            <span style={{ fontWeight: "bold" }}>{text}</span>
                          ),
                        },
                        {
                          title: "名称",
                          dataIndex: "name",
                          key: "name",
                          width: 120,
                          render: (text) => (
                            <span style={{ color: "#8c8c8c" }}>{text}</span>
                          ),
                        },
                        {
                          title: "达标指标",
                          dataIndex: "reached_indicators",
                          key: "reached_indicators",
                          render: (indicators) => (
                            <Space size={4}>
                              {indicators.map((ind, idx) => (
                                <Tag key={idx} color="success">
                                  {ind.ma_type}
                                </Tag>
                              ))}
                            </Space>
                          ),
                        },
                        {
                          title: "现价",
                          dataIndex: "current_price",
                          key: "current_price",
                          width: 100,
                          render: (price) => `¥${price?.toFixed(2)}`,
                        },
                        {
                          title: "最大偏离",
                          dataIndex: "max_deviation_percent",
                          key: "max_deviation_percent",
                          width: 100,
                          render: (percent) => (
                            <span
                              style={{ color: "#52c41a", fontWeight: "bold" }}
                            >
                              +{percent?.toFixed(2)}%
                            </span>
                          ),
                        },
                      ]}
                    />
                    {reachedTotal > reachedPageSize && (
                      <div style={{ marginTop: 16, textAlign: "right" }}>
                        <Pagination
                          current={reachedPage}
                          pageSize={reachedPageSize}
                          total={reachedTotal}
                          onChange={handleReachedPageChange}
                          showSizeChanger
                          showTotal={(total) => `共 ${total} 条`}
                          pageSizeOptions={["10", "20", "50"]}
                        />
                      </div>
                    )}
                  </>
                ) : (
                  <Empty
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                    description="暂无达标个股"
                  />
                )}
              </Card>

              {/* 趋势图表 */}
              <Card title="近 7 日趋势">{renderTrendChart()}</Card>
            </>
          ) : isNonTradingDay ? (
            /* 非交易日友好提示 */
            <div
              style={{
                padding: "48px 24px",
                textAlign: "center",
                background: "#fafafa",
                borderRadius: "8px",
              }}
            >
              <ClockCircleOutlined
                style={{ fontSize: "64px", color: "#faad14", marginBottom: 24 }}
              />
              <Title level={4} style={{ marginBottom: 8 }}>
                该日期为非交易日
              </Title>
              <Text type="secondary" style={{ fontSize: "16px" }}>
                {tradingDayInfo?.reason === "周末"
                  ? "股票市场周末休市"
                  : tradingDayInfo?.reason === "节假日"
                    ? "股票市场节假日休市"
                    : "该日期市场休市"}
              </Text>
              <div style={{ marginTop: 24 }}>
                <Text type="secondary">
                  💡
                  提示：您可以使用上方左右箭头切换日期，或点击日期打开日历选择历史交易日
                </Text>
              </div>
            </div>
          ) : (
            <Empty description="加载中..." />
          )}
        </Spin>
      </Card>
    </div>
  );
};

export default DailyReport;
