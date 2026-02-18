/**
 * 股票列表组件 - 已升级为移动平均线(MA)自动预警系统 + 智能缓存 + 性能优化
 */
import { useState, useEffect, useMemo, useRef, useCallback } from "react";
import {
  Table,
  Button,
  Space,
  Modal,
  Form,
  Input,
  Select,
  message,
  Popconfirm,
  Tag,
  Card,
  Statistic,
  Row,
  Col,
  Tabs,
  Spin,
  Tooltip,
  Dropdown,
  Switch,
} from "antd";
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ReloadOutlined,
  LineChartOutlined,
  FilterOutlined,
  MoreOutlined,
  SettingOutlined,
  SyncOutlined,
  ClockCircleOutlined,
} from "@ant-design/icons";
import { stockApi } from "../services/api";
import StockChart from "./StockChart";

const { Option } = Select;

/**
 * 判断当前是否处于A股交易时间段
 * A股交易时间：9:30-11:30, 13:00-15:00
 * 注意：此函数只判断时间，不判断是否为交易日（交易日由后端 API 判断）
 * 性能优化：使用缓存避免重复计算
 */
let tradingTimeCache = { value: null, timestamp: 0 };
const TRADING_CACHE_TTL = 30000; // 30秒缓存

const isInTradingHours = () => {
  const now = Date.now();

  // 使用缓存
  if (
    tradingTimeCache.value !== null &&
    now - tradingTimeCache.timestamp < TRADING_CACHE_TTL
  ) {
    return tradingTimeCache.value;
  }

  const date = new Date();
  const hours = date.getHours();
  const minutes = date.getMinutes();
  const currentTime = hours * 60 + minutes;

  // 上午交易时间 9:30-11:30
  const morningStart = 9 * 60 + 30;
  const morningEnd = 11 * 60 + 30;
  // 下午交易时间 13:00-15:00
  const afternoonStart = 13 * 60;
  const afternoonEnd = 15 * 60;

  const result =
    (currentTime >= morningStart && currentTime <= morningEnd) ||
    (currentTime >= afternoonStart && currentTime <= afternoonEnd);

  tradingTimeCache = { value: result, timestamp: now };
  return result;
};

/**
 * 格式化缓存时间显示
 */
const formatCachedTime = (cachedAt) => {
  if (!cachedAt) return "";
  const date = new Date(cachedAt);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return "刚刚";
  if (diffMins < 60) return `${diffMins}分钟前`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}小时前`;
  return date.toLocaleDateString("zh-CN", {
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

// 自动刷新间隔（毫秒）
const AUTO_REFRESH_INTERVAL = 30000;

const StockList = ({ groupId, groups: parentGroups, onGroupsChange }) => {
  const [stocks, setStocks] = useState([]);
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingStock, setEditingStock] = useState(null);
  const [filterType, setFilterType] = useState("all"); // 'all', 'allReached', 'partiallyReached', 'allBelow'

  // 智能缓存相关状态
  const [isTradingDay, setIsTradingDay] = useState(false); // 是否为交易日（后端判断）
  const [isTrading, setIsTrading] = useState(false); // 是否处于交易中（交易日 + 交易时间）
  const [tradingDayReason, setTradingDayReason] = useState(""); // 交易日状态原因
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(true);
  const autoRefreshRef = useRef(null);

  // 判定股票指标达标状态的辅助函数
  const getStockStatus = (stock) => {
    const results = Object.values(stock.ma_results || {});
    if (results.length === 0) return "allBelow";

    const reachedCount = results.filter((res) => res.reached_target).length;

    if (reachedCount === results.length) return "allReached";
    if (reachedCount > 0) return "partiallyReached";
    return "allBelow";
  };
  const [searchText, setSearchText] = useState("");
  const [selectedRowKeys, setSelectedRowKeys] = useState([]);
  const [chartModalVisible, setChartModalVisible] = useState(false);
  const [selectedSymbol, setSelectedSymbol] = useState(null);
  const [charts, setCharts] = useState(null);
  const [chartLoading, setChartLoading] = useState(false);
  const [form] = Form.useForm();
  const prevGroupsRef = useRef(parentGroups);

  const loadStocks = async () => {
    setLoading(true);
    try {
      const data = await stockApi.getAllStocks(groupId, searchText);
      setStocks(data);
    } catch (error) {
      message.error("加载股票列表失败: " + error.message);
    } finally {
      setLoading(false);
    }
  };

  const loadGroups = async () => {
    try {
      const data = await stockApi.getAllGroups();
      setGroups(data);
    } catch (error) {
      console.error("加载分组失败", error);
    }
  };

  useEffect(() => {
    // 判断是否仅为新增分组：长度增加，且旧分组的 ID 和名称均未改变
    const isJustAdded =
      parentGroups &&
      prevGroupsRef.current &&
      parentGroups.length > prevGroupsRef.current.length &&
      prevGroupsRef.current.length > 0 && // 确保之前已经有数据，而非初次加载
      prevGroupsRef.current.every((oldG) =>
        parentGroups.some(
          (newG) => newG.id === oldG.id && newG.name === oldG.name,
        ),
      );

    // 更新引用供下一次对比
    prevGroupsRef.current = parentGroups;

    // 如果只是新增分组，不触发 loadStocks
    if (isJustAdded) return;

    const timer = setTimeout(() => {
      loadStocks();
    }, 300); // 搜索防抖
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [groupId, searchText, parentGroups]);

  useEffect(() => {
    loadGroups();
  }, []);

  // 检查交易日状态（调用后端 API）
  const checkTradingDayStatus = async () => {
    try {
      const data = await stockApi.checkTradingDay();
      const newIsTradingDay = data.is_trading_day;
      const newReason = data.reason;

      // 判断是否处于交易中：交易日 + 交易时间
      const newIsTrading = newIsTradingDay && isInTradingHours();

      // 状态变化时更新
      if (newIsTradingDay !== isTradingDay) {
        setIsTradingDay(newIsTradingDay);
        setTradingDayReason(newReason);

        if (newIsTradingDay) {
          message.info("今日为交易日");
        } else {
          message.info(`今日为非交易日（${newReason}），自动刷新已暂停`);
        }
      }

      // 更新交易状态
      if (newIsTrading !== isTrading) {
        setIsTrading(newIsTrading);
        if (newIsTrading && newIsTradingDay) {
          message.info("已进入交易时间，自动刷新已启用");
        } else if (!newIsTrading && isTrading) {
          message.info("已离开交易时间，自动刷新已暂停");
        }
      }
    } catch (error) {
      console.error("检查交易日失败:", error);
      // API 失败时，使用纯前端判断作为降级方案
      const fallbackIsTrading = isInTradingHours();
      setIsTrading(fallbackIsTrading);
      setIsTradingDay(fallbackIsTrading);
      setTradingDayReason("API 降级判断");
    }
  };

  // 初始化时检查交易日
  useEffect(() => {
    checkTradingDayStatus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 自动刷新逻辑
  useEffect(() => {
    // 清除已有的定时器
    if (autoRefreshRef.current) {
      clearInterval(autoRefreshRef.current);
      autoRefreshRef.current = null;
    }

    // 只有在交易时间且开启了自动刷新时才启用
    if (autoRefreshEnabled && isTrading) {
      autoRefreshRef.current = setInterval(() => {
        loadStocks();
      }, AUTO_REFRESH_INTERVAL);
    }

    return () => {
      if (autoRefreshRef.current) {
        clearInterval(autoRefreshRef.current);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoRefreshEnabled, isTrading, groupId, searchText]);

  // 每分钟检查一次交易状态（交易日 + 交易时间）
  useEffect(() => {
    const checkTradingStatus = () => {
      // 每5分钟重新检查交易日（应对跨天情况）
      const now = new Date();
      if (now.getMinutes() % 5 === 0) {
        checkTradingDayStatus();
      } else {
        // 其他时间只检查交易时间段变化
        const newIsTrading = isTradingDay && isInTradingHours();
        if (newIsTrading !== isTrading) {
          setIsTrading(newIsTrading);
          if (newIsTrading) {
            message.info("已进入交易时间，自动刷新已启用");
          } else {
            message.info("已离开交易时间，自动刷新已暂停");
          }
        }
      }
    };

    const interval = setInterval(checkTradingStatus, 60000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isTrading, isTradingDay]);

  // 根据筛选类型过滤数据
  const filteredStocks = useMemo(() => {
    if (filterType === "all") return stocks;
    return stocks.filter((s) => getStockStatus(s) === filterType);
  }, [stocks, filterType]);

  const showChartModal = async (symbol, name) => {
    setSelectedSymbol({ symbol, name });
    setChartModalVisible(true);
    setChartLoading(true);
    try {
      const data = await stockApi.getStockCharts(symbol);
      setCharts(data);
    } catch (error) {
      message.error("获取趋势图失败: " + error.message);
    } finally {
      setChartLoading(false);
    }
  };

  const showModal = (stock = null) => {
    loadGroups(); // 每次打开弹窗时重新加载分组列表，确保数据最新
    setEditingStock(stock);
    if (stock) {
      form.setFieldsValue({
        symbol: stock.symbol,
        name: stock.name,
        ma_types: stock.ma_types || ["MA5"],
        group_ids: stock.group_ids || [],
      });
    } else {
      form.resetFields();
      form.setFieldsValue({
        ma_types: ["MA5"],
        group_ids: groupId ? [parseInt(groupId)] : [],
      });
    }
    setModalVisible(true);
  };

  const handleCancel = () => {
    setModalVisible(false);
    setEditingStock(null);
    form.resetFields();
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (editingStock) {
        await stockApi.updateStock(editingStock.id, {
          name: values.name,
          ma_types: values.ma_types,
          group_ids: values.group_ids,
        });
        message.success("指标设置更新成功!");
        // 分组可能有变化，通知父组件刷新分组列表
        if (onGroupsChange) onGroupsChange();
      } else {
        await stockApi.createStock(values);
        message.success("股票已添加，正在计算指标...");
        // 新增股票可能有分组，通知父组件刷新分组列表
        if (onGroupsChange) onGroupsChange();
      }
      handleCancel();
      loadStocks();
    } catch (error) {
      message.error(
        "操作失败: " + (error.response?.data?.detail || error.message),
      );
    }
  };

  const handleDelete = async (id, stock) => {
    try {
      if (groupId) {
        // 在分组视图下，从当前分组中移除（保留其他分组）
        const newGroupIds = (stock.group_ids || []).filter(
          (id) => id !== parseInt(groupId),
        );
        await stockApi.updateStock(id, { group_ids: newGroupIds });
        message.success("已成功从当前分组移出!");
        // 从分组移出，通知父组件刷新分组列表
        if (onGroupsChange) onGroupsChange();
      } else {
        // 在全部视图下，彻底删除
        await stockApi.deleteStock(id);
        message.success("股票记录已删除!");
        // 删除股票，通知父组件刷新分组列表
        if (onGroupsChange) onGroupsChange();
      }
      loadStocks();
    } catch (error) {
      message.error("操作失败: " + error.message);
    }
  };

  const handleUpdatePrice = async (symbol) => {
    // 非交易时间提示
    if (!isTrading) {
      if (!isTradingDay) {
        message.warning(
          `今日为${tradingDayReason || "非交易日"}，将使用缓存数据`,
        );
      } else {
        message.info("当前非交易时间，将使用缓存数据");
      }
    }

    try {
      const result = await stockApi.updateStockPriceBySymbol(symbol);
      message.success(result.message);

      // 只更新单只股票的数据，而不是刷新整个列表
      setStocks((prevStocks) =>
        prevStocks.map((stock) => {
          if (stock.symbol === symbol) {
            return {
              ...stock,
              current_price: result.current_price,
              ma_results: result.ma_results,
              is_realtime: result.is_realtime,
              updated_at: new Date().toISOString(),
            };
          }
          return stock;
        }),
      );
    } catch (error) {
      message.error("更新失败: " + error.message);
    }
  };

  const handleBatchDelete = async () => {
    if (selectedRowKeys.length === 0) return;

    try {
      setLoading(true);
      if (groupId) {
        await stockApi.batchRemoveFromGroup(selectedRowKeys, parseInt(groupId));
        message.success(
          `已成功从当前分组移出 ${selectedRowKeys.length} 只股票!`,
        );
        // 从分组批量移出，通知父组件刷新分组列表
        if (onGroupsChange) onGroupsChange();
      } else {
        await stockApi.batchDeleteStocks(selectedRowKeys);
        message.success(`已成功删除 ${selectedRowKeys.length} 只股票记录!`);
        // 批量删除股票，通知父组件刷新分组列表
        if (onGroupsChange) onGroupsChange();
      }
      setSelectedRowKeys([]);
      loadStocks();
    } catch (error) {
      message.error("操作失败: " + error.message);
    } finally {
      setLoading(false);
    }
  };

  const onSelectChange = (newSelectedRowKeys) => {
    setSelectedRowKeys(newSelectedRowKeys);
  };

  const rowSelection = {
    selectedRowKeys,
    onChange: onSelectChange,
  };

  const handleUpdateAllPrices = async () => {
    // 非交易时间提示
    if (!isTrading) {
      if (!isTradingDay) {
        message.warning(
          `今日为${tradingDayReason || "非交易日"}，将使用缓存数据`,
        );
      } else {
        message.info("当前非交易时间，将使用缓存数据");
      }
    }

    setLoading(true);
    try {
      const result = await stockApi.updateAllPrices();
      message.success(result.message);
      loadStocks();
    } catch (error) {
      message.error("批量更新失败: " + error.message);
    } finally {
      setLoading(false);
    }
  };

  const stats = useMemo(() => {
    const counts = {
      total: stocks.length,
      allReached: 0,
      partiallyReached: 0,
      allBelow: 0,
    };

    stocks.forEach((s) => {
      const status = getStockStatus(s);
      if (status === "allReached") counts.allReached++;
      else if (status === "partiallyReached") counts.partiallyReached++;
      else counts.allBelow++;
    });

    return counts;
  }, [stocks]);

  const columns = [
    {
      title: "股票信息",
      key: "stock_info",
      width: 150,
      render: (_, record) => (
        <div
          style={{ cursor: "pointer" }}
          onClick={() => showChartModal(record.symbol, record.name)}
        >
          <div
            style={{ fontWeight: "bold", color: "#1890ff", fontSize: "14px" }}
          >
            {record.symbol}
          </div>
          <div style={{ fontSize: "12px", color: "#8c8c8c" }}>
            {record.name}
          </div>
        </div>
      ),
    },
    {
      title: "所属分组",
      dataIndex: "group_names",
      key: "group_names",
      width: 120,
      render: (names) => (
        <Space size={[0, 4]} wrap>
          {names && names.length > 0 ? (
            names.map((name) => (
              <Tag color="cyan" key={name} style={{ margin: "2px" }}>
                {name}
              </Tag>
            ))
          ) : (
            <Tag color="default">未分组</Tag>
          )}
        </Space>
      ),
    },
    {
      title: "现价",
      dataIndex: "current_price",
      key: "current_price",
      width: 90,
      sorter: (a, b) => (a.current_price || 0) - (b.current_price || 0),
      render: (price) => (price ? `¥${price.toFixed(2)}` : "-"),
    },
    {
      title: "数据来源",
      key: "data_source",
      width: 100,
      render: (_, record) => {
        const isRealtime = record.is_realtime;
        return (
          <Tooltip
            title={
              isRealtime
                ? "数据为实时获取"
                : `数据来自缓存，更新于 ${formatCachedTime(record.updated_at)}`
            }
          >
            <Tag
              color={isRealtime ? "success" : "default"}
              style={{ cursor: "help" }}
            >
              {isRealtime ? (
                <>
                  <SyncOutlined spin style={{ marginRight: 4 }} />
                  实时
                </>
              ) : (
                <>
                  <ClockCircleOutlined style={{ marginRight: 4 }} />
                  缓存
                </>
              )}
            </Tag>
          </Tooltip>
        );
      },
    },
    {
      title: "指标详情 (均线价格 / 偏离度)",
      key: "ma_details",
      render: (_, record) => {
        const types = record.ma_types || [];
        const results = record.ma_results || {};

        return (
          <Space size={[4, 8]} wrap>
            {types.map((type) => {
              const res = results[type];
              if (!res || res.ma_price === null) {
                return (
                  <Tag
                    key={type}
                    color="default"
                    style={{ borderRadius: "4px" }}
                  >
                    {type}: 计算中
                  </Tag>
                );
              }

              const isAbove = res.reached_target;
              const diffPercent = res.price_difference_percent.toFixed(2);
              const sign = res.price_difference >= 0 ? "+" : "";

              return (
                <Tooltip
                  key={type}
                  title={
                    <div style={{ fontSize: "12px" }}>
                      <p style={{ margin: 0 }}>指标类型: {type}</p>
                      <p style={{ margin: 0, fontWeight: "bold" }}>
                        当前股价: ¥{record.current_price?.toFixed(2)}
                      </p>
                      <p style={{ margin: 0 }}>
                        均线价格: ¥{res.ma_price.toFixed(2)}
                      </p>
                      <p style={{ margin: 0 }}>
                        偏离数值: {sign}
                        {res.price_difference.toFixed(2)}
                      </p>
                    </div>
                  }
                >
                  <Tag
                    color={isAbove ? "green" : "red"}
                    style={{
                      borderRadius: "4px",
                      padding: "2px 10px",
                      margin: "2px",
                      cursor: "help",
                      border: "1px solid",
                      borderColor: isAbove ? "#b7eb8f" : "#ffa39e",
                      display: "flex",
                      alignItems: "center",
                      gap: "4px",
                    }}
                  >
                    <span style={{ fontWeight: "bold", fontSize: "12px" }}>
                      {type}
                    </span>
                    <span
                      style={{
                        fontSize: "12px",
                        borderLeft: "1px solid rgba(0,0,0,0.1)",
                        paddingLeft: "4px",
                      }}
                    >
                      ¥{res.ma_price.toFixed(2)}
                    </span>
                    <span
                      style={{
                        marginLeft: "2px",
                        fontSize: "11px",
                        fontWeight: "bold",
                        opacity: 0.9,
                      }}
                    >
                      ({sign}
                      {diffPercent}%)
                    </span>
                  </Tag>
                </Tooltip>
              );
            })}
          </Space>
        );
      },
    },
    {
      title: "操作",
      key: "action",
      width: 140,
      fixed: "right",
      render: (_, record) => {
        const actionItems = [
          {
            key: "chart",
            label: "查看图表",
            icon: <LineChartOutlined />,
            onClick: () => showChartModal(record.symbol, record.name),
          },
          {
            key: "edit",
            label: "设置指标",
            icon: <SettingOutlined />,
            onClick: () => showModal(record),
          },
          {
            type: "divider",
          },
          {
            key: "delete",
            label: groupId ? "从分组移出" : "彻底删除",
            icon: <DeleteOutlined />,
            danger: true,
            onClick: () => {
              Modal.confirm({
                title: "确认操作",
                content: groupId
                  ? `确定要将 ${record.name} 从当前分组移出吗？`
                  : `确定要彻底删除 ${record.name} 的监控记录吗？`,
                okText: "确认",
                cancelText: "取消",
                okButtonProps: { danger: true },
                onOk: () => handleDelete(record.id, record),
              });
            },
          },
        ];

        return (
          <Space size="small">
            <Tooltip title="查看图表">
              <Button
                type="text"
                shape="circle"
                icon={<LineChartOutlined style={{ color: "#52c41a" }} />}
                onClick={() => showChartModal(record.symbol, record.name)}
              />
            </Tooltip>
            <Tooltip title="刷新价格">
              <Button
                type="text"
                shape="circle"
                icon={<ReloadOutlined style={{ color: "#1890ff" }} />}
                onClick={() => handleUpdatePrice(record.symbol)}
              />
            </Tooltip>
            <Dropdown menu={{ items: actionItems }} trigger={["click"]}>
              <Button type="text" shape="circle" icon={<MoreOutlined />} />
            </Dropdown>
          </Space>
        );
      },
    },
  ];

  // 卡片公共样式
  const getCardStyle = (type) => ({
    cursor: "pointer",
    transition: "all 0.3s",
    border: filterType === type ? "2px solid #1890ff" : "1px solid #f0f0f0",
    backgroundColor: filterType === type ? "#e6f7ff" : "#fff",
    boxShadow:
      filterType === type ? "0 4px 12px rgba(24, 144, 255, 0.2)" : "none",
  });

  const injectStyles = (
    <style>
      {`
        .row-all-reached { background-color: #f6ffed !important; }
        .row-all-below { background-color: #fff1f0 !important; }
        .ant-table-row:hover .row-all-reached { background-color: #f0f9eb !important; }
        .ant-table-row:hover .row-all-below { background-color: #ffefee !important; }
      `}
    </style>
  );

  return (
    <div style={{ padding: "24px" }}>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={6}>
          <Card
            hoverable
            style={getCardStyle("all")}
            onClick={() => setFilterType("all")}
          >
            <Statistic title="监控总数" value={stats.total} />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card
            hoverable
            style={getCardStyle("allReached")}
            onClick={() => setFilterType("allReached")}
          >
            <Statistic
              title="全达标"
              value={stats.allReached}
              styles={{ content: { color: "#3f8600" } }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card
            hoverable
            style={getCardStyle("partiallyReached")}
            onClick={() => setFilterType("partiallyReached")}
          >
            <Statistic
              title="部分达标"
              value={stats.partiallyReached}
              styles={{ content: { color: "#1890ff" } }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card
            hoverable
            style={getCardStyle("allBelow")}
            onClick={() => setFilterType("allBelow")}
          >
            <Statistic
              title="全低于"
              value={stats.allBelow}
              styles={{ content: { color: "#cf1322" } }}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title={
          <Space>
            <LineChartOutlined />
            <span>移动平均线 (MA) 预警监控</span>
            {/* 交易时间状态标识 */}
            {isTrading ? (
              <Tag color="processing" icon={<SyncOutlined spin />}>
                交易中
              </Tag>
            ) : isTradingDay ? (
              <Tag color="warning" icon={<ClockCircleOutlined />}>
                休市（非交易时间）
              </Tag>
            ) : (
              <Tag color="default" icon={<ClockCircleOutlined />}>
                休市（{tradingDayReason || "非交易日"}）
              </Tag>
            )}
            {filterType !== "all" && (
              <Tag
                closable
                color="orange"
                onClose={() => setFilterType("all")}
                icon={<FilterOutlined />}
              >
                当前查看:{" "}
                {filterType === "allReached"
                  ? "全达标"
                  : filterType === "partiallyReached"
                    ? "部分达标"
                    : "全低于"}{" "}
                (点击清除)
              </Tag>
            )}
          </Space>
        }
        extra={
          <Space wrap>
            <Input.Search
              placeholder="搜索代码或名称"
              allowClear
              onSearch={setSearchText}
              onChange={(e) => setSearchText(e.target.value)}
              style={{ width: 200 }}
            />
            {selectedRowKeys.length > 0 && (
              <Popconfirm
                title={`确认批量${groupId ? "移出" : "删除"} ${selectedRowKeys.length} 项?`}
                onConfirm={handleBatchDelete}
              >
                <Button type="primary" danger icon={<DeleteOutlined />}>
                  批量{groupId ? "移出" : "删除"}
                </Button>
              </Popconfirm>
            )}
            <Button
              icon={<ReloadOutlined />}
              onClick={handleUpdateAllPrices}
              loading={loading}
            >
              全量刷新
            </Button>
            <Tooltip
              title={
                isTrading
                  ? autoRefreshEnabled
                    ? "自动刷新已启用（30秒间隔）"
                    : "自动刷新已暂停"
                  : isTradingDay
                    ? "当前非交易时间（9:30-11:30, 13:00-15:00）"
                    : `今日为${tradingDayReason || "非交易日"}，自动刷新不可用`
              }
            >
              <Space style={{ marginLeft: 8 }}>
                <SyncOutlined
                  spin={autoRefreshEnabled && isTrading}
                  style={{ color: isTrading ? "#52c41a" : "#999" }}
                />
                <Switch
                  size="small"
                  checked={autoRefreshEnabled}
                  onChange={setAutoRefreshEnabled}
                  disabled={!isTrading}
                />
                <span style={{ fontSize: 12, color: "#666" }}>
                  {isTrading
                    ? "自动刷新"
                    : isTradingDay
                      ? "非交易时间"
                      : "休市"}
                </span>
              </Space>
            </Tooltip>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => showModal()}
            >
              添加股票
            </Button>
          </Space>
        }
      >
        {injectStyles}
        <Table
          rowSelection={rowSelection}
          columns={columns}
          dataSource={filteredStocks}
          rowKey="id"
          loading={loading}
          rowClassName={(record) => {
            const status = getStockStatus(record);
            if (status === "allReached") return "row-all-reached";
            if (status === "allBelow") return "row-all-below";
            return "";
          }}
          pagination={{
            pageSize: 10,
            showTotal: (total) => `共 ${total} 条监控`,
          }}
        />
      </Card>

      <Modal
        title={editingStock ? "修改预警设置" : "添加监控股票"}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={handleCancel}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="symbol"
            label="股票代码"
            rules={[{ required: true, message: "请输入代码" }]}
          >
            <Input
              placeholder="如: 600519.SS 或 AAPL"
              disabled={!!editingStock}
              onPressEnter={handleSubmit}
            />
          </Form.Item>

          <Form.Item
            name="ma_types"
            label="预警均线 (日线指标)"
            rules={[{ required: true, message: "请选择至少一个指标" }]}
          >
            <Select mode="multiple" placeholder="选择多个指标以同时监控">
              <Option value="MA5">MA5 (5日均线)</Option>
              <Option value="MA10">MA10 (10日均线)</Option>
              <Option value="MA20">MA20 (20日均线)</Option>
              <Option value="MA30">MA30 (30日均线)</Option>
              <Option value="MA60">MA60 (60日均线)</Option>
              <Option value="MA120">MA120 (半年线)</Option>
              <Option value="MA250">MA250 (年线)</Option>
            </Select>
          </Form.Item>

          <Form.Item name="group_ids" label="所属分组">
            <Select
              mode="multiple"
              placeholder="请选择分组（可多选）"
              allowClear
              style={{ width: "100%" }}
            >
              {groups.map((group) => (
                <Option key={group.id} value={group.id}>
                  {group.name}
                </Option>
              ))}
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={
          selectedSymbol
            ? `${selectedSymbol.name} (${selectedSymbol.symbol}) 趋势图`
            : "趋势图"
        }
        open={chartModalVisible}
        onCancel={() => {
          setChartModalVisible(false);
          setCharts(null);
          setSelectedSymbol(null);
        }}
        footer={null}
        width={650}
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

export default StockList;
