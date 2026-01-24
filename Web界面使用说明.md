# Web界面使用说明

## 问题修复

已修复以下问题：
1. ✅ 添加了CORS支持，允许浏览器访问API
2. ✅ 修复了场景列表加载逻辑，直接使用已知的demo-park场景
3. ✅ API服务已重启，所有端点正常工作

## 使用步骤

### 1. 确保API服务运行
```bash
# 检查服务状态
curl http://localhost:8000/healthz

# 如果服务未运行，启动服务
./start_api.sh
```

### 2. 打开Web界面
在浏览器中打开 `qa_chat_demo.html` 文件：
```bash
open qa_chat_demo.html
```

或者直接双击文件在浏览器中打开。

### 3. 选择场景
在页面顶部的下拉菜单中选择：
- **示范园区综合能源规划 (demo-park)**

### 4. 开始对话
选择场景后，界面会显示：
- 欢迎消息
- 4个建议问题（可点击快速提问）
- 输入框已启用

### 5. 提问方式

#### 方式1：点击建议问题
界面会显示4个建议问题：
- 有哪些推荐的减排措施？
- 园区的基线排放是多少？
- 有哪些政策支持和补贴？
- 屋顶光伏的具体情况如何？

直接点击即可提问。

#### 方式2：手动输入问题
在底部输入框中输入任何问题，按回车或点击"发送"按钮。

## 功能特点

### 智能问答
- 基于生成的报告内容回答问题
- 显示置信度（高/中/低）
- 提供信息来源引用

### 美观界面
- 聊天式对话界面
- 用户消息显示在右侧（紫色）
- AI回复显示在左侧（白色）
- 实时加载动画

### 建议问题
- 自动加载场景相关的建议问题
- 点击即可快速提问
- 帮助用户快速了解报告内容

## 测试API连接

如果界面无法正常工作，运行测试脚本：
```bash
./test_web_api.sh
```

这会测试：
- 健康检查端点
- 建议问题端点
- 问答功能端点

## 常见问题

### Q: 页面显示"无法加载场景"
**A**: 检查API服务是否运行：
```bash
curl http://localhost:8000/healthz
```

### Q: 提问后没有响应
**A**: 
1. 打开浏览器开发者工具（F12）查看Console
2. 检查是否有CORS错误
3. 确认API服务正常运行

### Q: 建议问题不显示
**A**: 
1. 确保选择了场景
2. 检查outputs/demo-park/artifacts/qa_index.json文件是否存在
3. 重新运行 `python multi_energy_agent/runner.py` 生成报告

## 技术细节

### API端点
- `GET /healthz` - 健康检查
- `GET /api/v1/scenarios/{scenario_id}/qa/suggestions` - 获取建议问题
- `POST /api/v1/scenarios/{scenario_id}/qa?question=xxx` - 提问

### 数据来源
- 报告文件：`outputs/demo-park/report.md`
- QA索引：`outputs/demo-park/artifacts/qa_index.json`

### CORS配置
API已配置允许所有来源访问（开发环境）。生产环境应限制具体域名。
