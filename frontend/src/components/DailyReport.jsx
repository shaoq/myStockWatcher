/**
 * 每日报告页面 - 展示股票指标变化和趋势，支持查看历史报告和交易日判断
 */
import { useState, useEffect } from "react";
import {
  Card,
  Row,
  Col,
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
  Modal,
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
} from "@ant-design/icons";
import dayjs from "dayjs";
import { stockApi } from "../services/api";
import StockChart from "./StockChart";

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

/**
 * 按偏离度升序排序（未达标股票用，最负的排前面）
 * @param {Array} items - 项目数组
 * @returns {Array} - 排序后的数组
 */
const sortBelowItemsByDeviation = (items) => {
  if (!items) return [];
  return [...items].sort((a, b) => {
    const devA = a.price_difference_percent || 0;
    const devB = b.price_difference_percent || 0;
    return devA - devB; // 升序（最负的排前面）
  });
};

/**
 * 按未达标类型分组（new_fall 优先）
 * @param {Array} items - 未达标股票数组
 * @returns {Object} - { new_fall: [...], continuous_below: [...] }
 */
const groupByFallType = (items) => {
  if (!items || items.length === 0)
    return { new_fall: [], continuous_below: [] };
  return items.reduce(
    (acc, item) => {
      const fallType = item.fall_type || "continuous_below";
      if (!acc[fallType]) {
        acc[fallType] = [];
      }
      acc[fallType].push(item);
      return acc;
    },
    { new_fall: [], continuous_below: [] },
  );
};

/**
 * 将聚合的达标股票数据展平为扁平数组（每个指标一条记录）
 * @param {Array} reachedStocks - 聚合的达标股票数组
 * @returns {Array} - 扁平化的数组，每个元素包含 stock 信息和单个指标信息
 */
const flattenReachedStocks = (reachedStocks) => {
  if (!reachedStocks || reachedStocks.length === 0) return [];

  const flattened = [];
  reachedStocks.forEach((stock) => {
    stock.reached_indicators.forEach((indicator) => {
      flattened.push({
        stock_id: stock.stock_id,
        symbol: stock.symbol,
        name: stock.name,
        current_price: stock.current_price,
        ma_type: indicator.ma_type,
        ma_price: indicator.ma_price,
        price_difference_percent: indicator.price_difference_percent,
        reach_type: indicator.reach_type || "new_reach", // 向后兼容
      });
    });
  });

  return flattened;
};

/**
 * 按 reach_type 分组
 * @param {Array} items - 达标股票数组
 * @returns {Object} - { new_reach: [...], continuous_reach: [...] }
 */
const groupByReachType = (items) => {
  if (!items || items.length === 0)
    return { new_reach: [], continuous_reach: [] };
  return items.reduce(
    (acc, item) => {
      const reachType = item.reach_type || "new_reach";
      if (!acc[reachType]) {
        acc[reachType] = [];
      }
      acc[reachType].push(item);
      return acc;
    },
    { new_reach: [], continuous_reach: [] },
  );
};

const DailyReport = () => {
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [checkingTradingDay, setCheckingTradingDay] = useState(false); // 交易日检查状态
  const [snapshotStatus, setSnapshotStatus] = useState(null);
  const [report, setReport] = useState(null);
  const [availableDates, setAvailableDates] = useState([]);
  const [tradingDays, setTradingDays] = useState([]); // 当前月份的交易日列表
  const [selectedDate, setSelectedDate] = useState(null);
  const [prevDate, setPrevDate] = useState(null);
  const [nextDate, setNextDate] = useState(null);
  const [tradingDayInfo, setTradingDayInfo] = useState(null); // 交易日信息
  const [isNonTradingDay, setIsNonTradingDay] = useState(false); // 是否为非交易日
  const [chartModalVisible, setChartModalVisible] = useState(false); // 趋势图Modal
  const [selectedSymbol, setSelectedSymbol] = useState(null); // 选中的股票

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
      const reportData = await stockApi.getDailyReport(dateStr);
      setReport(reportData);

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

  // 显示趋势图Modal
  const showChartModal = (symbol, name) => {
    setSelectedSymbol({ symbol, name });
    setChartModalVisible(true);
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

  // 渲染未达标股票（含 fall_type 分类）
  const renderBelowStocksWithFallType = (items) => {
    if (!items || items.length === 0) {
      return (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="无未达标股票"
        />
      );
    }

    // 按 MA 类型分组
    const grouped = groupByMA(items);
    const sortedKeys = getSortedGroupKeys(grouped);

    return (
      <Collapse defaultActiveKey={sortedKeys} ghost expandIconPosition="end">
        {sortedKeys.map((maType) => {
          const groupItems = sortBelowItemsByDeviation(grouped[maType]);
          // 按 fall_type 分组
          const { new_fall, continuous_below } = groupByFallType(groupItems);

          return (
            <Panel
              key={maType}
              header={
                <Space>
                  <Tag color="error">{maType}</Tag>
                  <Text strong>{maType}</Text>
                  <Text type="secondary">({groupItems.length}只)</Text>
                </Space>
              }
            >
              {/* 新跌破 - 红色 */}
              {new_fall.length > 0 && (
                <div style={{ marginBottom: 8 }}>
                  <div
                    style={{
                      marginBottom: 4,
                      fontWeight: "bold",
                      color: "#ff4d4f",
                    }}
                  >
                    🔴 新跌破 ({new_fall.length}只)
                  </div>
                  <List
                    dataSource={new_fall}
                    renderItem={(item) => renderBelowItem(item, "new_fall")}
                    size="small"
                  />
                </div>
              )}
              {/* 持续未达标 - 黄色 */}
              {continuous_below.length > 0 && (
                <div>
                  <div
                    style={{
                      marginBottom: 4,
                      fontWeight: "bold",
                      color: "#faad14",
                    }}
                  >
                    🟡 持续未达标 ({continuous_below.length}只)
                  </div>
                  <List
                    dataSource={continuous_below}
                    renderItem={(item) =>
                      renderBelowItem(item, "continuous_below")
                    }
                    size="small"
                  />
                </div>
              )}
            </Panel>
          );
        })}
      </Collapse>
    );
  };

  // 渲染单个未达标股票项
  const renderBelowItem = (item, fallType) => {
    const isNewFall = fallType === "new_fall";
    const tagColor = isNewFall ? "error" : "warning";

    return (
      <List.Item>
        <List.Item.Meta
          avatar={<Tag color={tagColor}>{item.ma_type}</Tag>}
          title={
            <Space>
              <span
                style={{
                  fontWeight: "bold",
                  cursor: "pointer",
                  color: "#1890ff",
                }}
                onClick={() => showChartModal(item.symbol, item.name)}
              >
                {item.symbol}
              </span>
              <span
                style={{ color: "#8c8c8c", cursor: "pointer" }}
                onClick={() => showChartModal(item.symbol, item.name)}
              >
                {item.name}
              </span>
            </Space>
          }
          description={
            <Space split={<Divider type="vertical" />}>
              <span>现价: ¥{item.current_price?.toFixed(2)}</span>
              <span>均线: ¥{item.ma_price?.toFixed(2)}</span>
              <span style={{ color: "#ff4d4f" }}>
                偏离: {item.price_difference_percent?.toFixed(2)}%
              </span>
            </Space>
          }
        />
      </List.Item>
    );
  };

  // 渲染单个达标股票项
  const renderReachedItem = (item, reachType) => {
    const isNewReach = reachType === "new_reach";
    const tagColor = isNewReach ? "success" : "#b7eb8f"; // 亮绿 vs 淡绿

    return (
      <List.Item>
        <List.Item.Meta
          avatar={<Tag color={tagColor}>{item.ma_type}</Tag>}
          title={
            <Space>
              <span
                style={{
                  fontWeight: "bold",
                  cursor: "pointer",
                  color: "#1890ff",
                }}
                onClick={() => showChartModal(item.symbol, item.name)}
              >
                {item.symbol}
              </span>
              <span
                style={{ color: "#8c8c8c", cursor: "pointer" }}
                onClick={() => showChartModal(item.symbol, item.name)}
              >
                {item.name}
              </span>
            </Space>
          }
          description={
            <Space split={<Divider type="vertical" />}>
              <span>现价: ¥{item.current_price?.toFixed(2)}</span>
              <span>均线: ¥{item.ma_price?.toFixed(2)}</span>
              <span style={{ color: "#52c41a" }}>
                偏离: +{item.price_difference_percent?.toFixed(2)}%
              </span>
            </Space>
          }
        />
      </List.Item>
    );
  };

  // 渲染达标股票（含 reach_type 分类）
  const renderReachedStocksWithReachType = (reachedStocks) => {
    if (!reachedStocks || reachedStocks.length === 0) {
      return (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="无达标股票" />
      );
    }

    // 展平数据：将聚合的 reached_stocks 转换为扁平数组
    const flattened = flattenReachedStocks(reachedStocks);

    // 按 MA 类型分组
    const grouped = groupByMA(flattened);
    const sortedKeys = getSortedGroupKeys(grouped);

    return (
      <Collapse defaultActiveKey={sortedKeys} ghost expandIconPosition="end">
        {sortedKeys.map((maType) => {
          const groupItems = sortItemsByDeviation(grouped[maType]);
          // 按 reach_type 分组
          const { new_reach, continuous_reach } = groupByReachType(groupItems);

          return (
            <Panel
              key={maType}
              header={
                <Space>
                  <Tag color="success">{maType}</Tag>
                  <Text strong>{maType}</Text>
                  <Text type="secondary">({groupItems.length}只)</Text>
                </Space>
              }
            >
              {/* 新增达标 - 亮绿色 */}
              {new_reach.length > 0 && (
                <div style={{ marginBottom: 8 }}>
                  <div
                    style={{
                      marginBottom: 4,
                      fontWeight: "bold",
                      color: "#52c41a",
                    }}
                  >
                    🟢 新增达标 ({new_reach.length}只)
                  </div>
                  <List
                    dataSource={new_reach}
                    renderItem={(item) => renderReachedItem(item, "new_reach")}
                    size="small"
                  />
                </div>
              )}
              {/* 持续达标 - 淡绿色 */}
              {continuous_reach.length > 0 && (
                <div>
                  <div
                    style={{
                      marginBottom: 4,
                      fontWeight: "bold",
                      color: "#73d13d",
                    }}
                  >
                    🟢 持续达标 ({continuous_reach.length}只)
                  </div>
                  <List
                    dataSource={continuous_reach}
                    renderItem={(item) =>
                      renderReachedItem(item, "continuous_reach")
                    }
                    size="small"
                  />
                </div>
              )}
            </Panel>
          );
        })}
      </Collapse>
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
              {/* 变化列表 */}
              <Row gutter={16} style={{ marginBottom: 24 }}>
                <Col xs={24} lg={12}>
                  <Card
                    title={
                      <Space>
                        <RiseOutlined style={{ color: "#52c41a" }} />
                        <span>达标个股</span>
                        <Tag color="success">
                          {report.reached_stocks?.length || 0}
                        </Tag>
                      </Space>
                    }
                    size="small"
                  >
                    {renderReachedStocksWithReachType(
                      report.reached_stocks || [],
                    )}
                  </Card>
                </Col>
                <Col xs={24} lg={12}>
                  <Card
                    title={
                      <Space>
                        <FallOutlined style={{ color: "#ff4d4f" }} />
                        <span>未达标个股</span>
                        <Tag color="error">
                          {report.all_below_stocks?.length || 0}
                        </Tag>
                      </Space>
                    }
                    size="small"
                  >
                    {renderBelowStocksWithFallType(
                      report.all_below_stocks || [],
                    )}
                  </Card>
                </Col>
              </Row>
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

      {/* 趋势图Modal */}
      <Modal
        title={
          selectedSymbol
            ? `${selectedSymbol.name} (${selectedSymbol.symbol}) 趋势图`
            : "趋势图"
        }
        open={chartModalVisible}
        onCancel={() => {
          setChartModalVisible(false);
          setSelectedSymbol(null);
        }}
        footer={null}
        width={750}
        centered
        destroyOnClose
      >
        {selectedSymbol && (
          <StockChart
            symbol={selectedSymbol.symbol}
            name={selectedSymbol.name}
          />
        )}
      </Modal>
    </div>
  );
};

export default DailyReport;
