/**
 * API服务层 - 处理所有与后端的HTTP请求
 */
import axios from "axios";

const API_BASE_URL = "http://localhost:9000";

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// 响应拦截器：统一处理 HTTP 错误
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // 网络错误（无响应）
    if (!error.response) {
      const networkError = new Error("网络连接失败，请检查网络");
      networkError.isNetworkError = true;
      return Promise.reject(networkError);
    }

    const { response } = error;
    const { status, data } = response;

    // 提取错误消息
    let message;
    if (data && data.detail) {
      // 后端返回的 detail 字段
      message = data.detail;
    } else if (status >= 500) {
      message = "服务器错误，请稍后重试";
    } else if (status >= 400) {
      message = `请求错误 (${status})`;
    } else {
      message = "未知错误";
    }

    // 构造统一的错误对象
    const apiError = new Error(message);
    apiError.status = status;
    apiError.detail = data?.detail;
    apiError.response = response;

    return Promise.reject(apiError);
  },
);

// 股票API服务
export const stockApi = {
  // 获取所有股票 (支持搜索)
  getAllStocks: async (groupId = null, query = "") => {
    const params = {};
    if (groupId) params.group_id = groupId;
    if (query) params.q = query;
    const response = await apiClient.get("/stocks/", { params });
    return response.data;
  },

  // 批量删除股票
  batchDeleteStocks: async (stockIds) => {
    const response = await apiClient.post("/stocks/batch-delete", stockIds);
    return response.data;
  },

  // 从分组中批量移出股票
  batchRemoveFromGroup: async (stockIds, groupId) => {
    const response = await apiClient.post(
      "/stocks/batch-remove-from-group",
      stockIds,
      {
        params: { group_id: groupId },
      },
    );
    return response.data;
  },

  // 获取单个股票
  getStock: async (id) => {
    const response = await apiClient.get(`/stocks/${id}`);
    return response.data;
  },

  // 创建股票
  createStock: async (stockData) => {
    const response = await apiClient.post("/stocks/", stockData);
    return response.data;
  },

  // 更新股票
  updateStock: async (id, stockData) => {
    const response = await apiClient.put(`/stocks/${id}`, stockData);
    return response.data;
  },

  // 删除股票
  deleteStock: async (id) => {
    const response = await apiClient.delete(`/stocks/${id}`);
    return response.data;
  },

  // 更新单个股票价格
  updateStockPrice: async (id) => {
    const response = await apiClient.post(`/stocks/${id}/update-price`);
    return response.data;
  },

  // 根据代码更新股票价格
  updateStockPriceBySymbol: async (symbol) => {
    const response = await apiClient.post(
      `/stocks/symbol/${symbol}/update-price`,
    );
    return response.data;
  },

  // 获取股票趋势图 URL
  getStockCharts: async (symbol) => {
    const response = await apiClient.get(`/stocks/symbol/${symbol}/charts`);
    return response.data;
  },

  // 更新所有股票价格
  updateAllPrices: async () => {
    const response = await apiClient.post("/stocks/update-all-prices");
    return response.data;
  },

  // --- 分组管理 ---

  // 获取所有分组
  getAllGroups: async () => {
    const response = await apiClient.get("/groups/");
    return response.data;
  },

  // 创建分组
  createGroup: async (groupData) => {
    const response = await apiClient.post("/groups/", groupData);
    return response.data;
  },

  // 删除分组
  deleteGroup: async (id) => {
    await apiClient.delete(`/groups/${id}`);
    return true;
  },

  // --- 快照管理 ---

  // 生成今日快照
  generateSnapshots: async () => {
    const response = await apiClient.post("/snapshots/generate");
    return response.data;
  },

  // 检查今日快照
  checkTodaySnapshots: async () => {
    const response = await apiClient.get("/snapshots/check-today");
    return response.data;
  },

  // 获取所有快照日期
  getSnapshotDates: async () => {
    const response = await apiClient.get("/snapshots/dates");
    return response.data;
  },

  // --- 每日报告 ---

  // 获取每日报告（支持指定日期）
  getDailyReport: async (targetDate = null) => {
    const params = {};
    if (targetDate) {
      params.target_date = targetDate;
    }
    const response = await apiClient.get("/reports/daily", { params });
    return response.data;
  },

  // 获取趋势数据
  getTrendData: async (days = 7) => {
    const response = await apiClient.get("/reports/trend", {
      params: { days },
    });
    return response.data;
  },
};

export default apiClient;
