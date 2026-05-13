# Chip Testing Flowcard Generator

芯片测试流程卡生成器 重庆邮电大学毕业设计项目

芯片测试流程卡生成器是一个面向芯片测试场景的知识库增强生成系统。项目支持上传和管理测试标准、手册等文档，通过 RAG 检索辅助大语言模型对话，并根据订单信息生成芯片测试流程卡。

## 功能模块

- 知识库管理：上传、查看、编辑、删除文档，并将文档向量化存入 Milvus。
- 知识库语义搜索：在指定文档中检索语义相近的内容片段。
- 对话系统：与大语言模型对话，并可选择知识库文档作为 RAG 数据源。
- 流程卡生成：根据订单文档或手动输入的订单要求生成芯片测试流程卡。

## 技术栈

- 后端：Python、FastAPI、vLLM、Milvus
- 前端：React、Vite、TypeScript、Nginx
- 部署：Docker Compose

## 目录结构

```text
backend/             后端服务代码
frontend/            前端 Web 界面
scripts/             一些辅助脚本
volume/              容器持久化数据目录
docker-compose.yml   Docker Compose 配置
```

## 部署

项目采用 Docker Compose 部署。在项目根目录执行：

```bash
docker compose up -d
```

## 访问

前端服务启动后，通过浏览器访问前端容器暴露的地址即可使用系统。前端会通过 Nginx 将 `/api/` 前缀的请求代理到后端接口。

## 说明

- 知识库文档向量化、对话生成和流程卡生成依赖后端模型与向量数据库服务正常运行。
- `docker-compose.yml` 可根据实际模型路径、端口、GPU 配置和持久化目录进行调整。
