import { useState, useEffect } from "react";
import {
  ConfigProvider,
  Layout,
  Typography,
  Menu,
  theme,
  Button,
  Modal,
  Form,
  Input,
  message,
  Space,
  Tag,
} from "antd";
import {
  PlusOutlined,
  FolderOutlined,
  GlobalOutlined,
  DeleteOutlined,
  BarChartOutlined,
} from "@ant-design/icons";
import StockList from "./components/StockList";
import DailyReport from "./components/DailyReport";
import { stockApi } from "./services/api";
import "./App.css";

const { Header, Content, Footer, Sider } = Layout;
const { Title } = Typography;

function App() {
  const [groups, setGroups] = useState([]);
  const [selectedGroupId, setSelectedGroupId] = useState("all");
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [form] = Form.useForm();

  const {
    token: { colorBgContainer, borderRadiusLG },
  } = theme.useToken();

  const loadGroups = async () => {
    try {
      const data = await stockApi.getAllGroups();
      setGroups(data);
    } catch (error) {
      message.error("加载分组失败");
    }
  };

  useEffect(() => {
    loadGroups();
  }, []);

  const handleAddGroup = async () => {
    try {
      const values = await form.validateFields();
      const newGroup = await stockApi.createGroup(values);
      message.success("分组创建成功");
      setIsModalVisible(false);
      form.resetFields();
      await loadGroups();
      // 自动选中新创建的分组
      if (newGroup && newGroup.id) {
        setSelectedGroupId(newGroup.id.toString());
      }
    } catch (error) {
      message.error("创建失败");
    }
  };

  const handleDeleteGroup = async (id, e) => {
    e.stopPropagation();
    Modal.confirm({
      title: "确认删除该分组？",
      content: "删除分组不会删除其中的股票，股票将变为“未分组”状态。",
      onOk: async () => {
        try {
          await stockApi.deleteGroup(id);
          message.success("分组已删除");
          if (selectedGroupId === id.toString()) {
            setSelectedGroupId("all");
          }
          loadGroups();
        } catch (error) {
          message.error("删除失败");
        }
      },
    });
  };

  const menuItems = [
    {
      key: "stock-group",
      icon: <GlobalOutlined />,
      label: "全部股票",
      children: [
        {
          key: "all",
          label: "全部",
        },
        ...groups.map((group) => ({
          key: group.id.toString(),
          icon: <FolderOutlined />,
          label: (
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <span>{group.name}</span>
              <Space>
                <Tag style={{ marginRight: 0 }}>{group.stock_count}</Tag>
                <DeleteOutlined
                  style={{ fontSize: "12px", color: "#ff4d4f" }}
                  onClick={(e) => handleDeleteGroup(group.id, e)}
                />
              </Space>
            </div>
          ),
        })),
      ],
    },
    {
      key: "daily-report",
      icon: <BarChartOutlined />,
      label: "每日报告",
    },
  ];

  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: "#1677ff",
          borderRadius: 6,
        },
      }}
    >
      <Layout style={{ minHeight: "100vh" }}>
        <Header
          style={{
            display: "flex",
            alignItems: "center",
            background: "#001529",
            padding: "0 24px",
            justifyContent: "space-between",
          }}
        >
          <Title level={3} style={{ color: "white", margin: 0 }}>
            📈 股票价格监控应用
          </Title>
        </Header>
        <Layout>
          <Sider width={250} style={{ background: colorBgContainer }}>
            <div style={{ padding: "16px", borderBottom: "1px solid #f0f0f0" }}>
              <Button
                type="primary"
                block
                icon={<PlusOutlined />}
                onClick={() => setIsModalVisible(true)}
              >
                新建分组
              </Button>
            </div>
            <Menu
              mode="inline"
              selectedKeys={[selectedGroupId]}
              defaultOpenKeys={["stock-group"]}
              style={{ height: "calc(100% - 64px)", borderRight: 0 }}
              items={menuItems}
              onClick={({ key }) => setSelectedGroupId(key)}
            />
          </Sider>
          <Content style={{ padding: "24px" }}>
            {selectedGroupId === "daily-report" ? (
              <DailyReport />
            ) : (
              <div
                style={{
                  background: colorBgContainer,
                  minHeight: 280,
                  padding: "0px",
                  borderRadius: borderRadiusLG,
                  overflow: "hidden",
                }}
              >
                <StockList
                  groupId={selectedGroupId === "all" ? null : selectedGroupId}
                  groups={groups}
                  onGroupsChange={loadGroups}
                />
              </div>
            )}
          </Content>
        </Layout>
        <Footer style={{ textAlign: "center" }}>
          Stock Info & Price Checker ©{new Date().getFullYear()} Created with
          Ant Design
        </Footer>

        <Modal
          title="新建分组"
          open={isModalVisible}
          onOk={handleAddGroup}
          onCancel={() => setIsModalVisible(false)}
        >
          <Form form={form} layout="vertical">
            <Form.Item
              name="name"
              label="分组名称"
              rules={[{ required: true, message: "请输入分组名称" }]}
            >
              <Input
                placeholder="例如：长期持有、科技板块"
                onPressEnter={handleAddGroup}
              />
            </Form.Item>
          </Form>
        </Modal>
      </Layout>
    </ConfigProvider>
  );
}

export default App;
