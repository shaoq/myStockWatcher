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
};

export default apiClient;
