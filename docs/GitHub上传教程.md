# GitHub 上传教程(Windows 手把手版)

跟着做,大约 40 分钟。每一步都可以直接复制命令。

---

## 第 1 步:注册 GitHub 账号(5分钟)

1. 打开 https://github.com ,点右上角 **Sign up**
2. 邮箱建议用常用的(QQ邮箱可以,但学生建议注册一个教育邮箱)
3. **用户名要认真起**:面试官会看到它。建议"名字+含义"的形式,如 `zhangwei-dev`,避免 `xxx_123456` 这种
4. 免费套餐(Free)就够了,一路下一步

## 第 2 步:配置 Git 身份(2分钟)

你已经装好了 Git。打开终端(VS Code 里按 `` Ctrl+` ``),执行(**换成你自己的名字和邮箱**,邮箱要和 GitHub 注册邮箱一致):

```bash
git config --global user.name "你的用户名"
git config --global user.email "你的邮箱"
```

验证:

```bash
git config --global user.name
git config --global user.email
```

## 第 3 步:在 GitHub 上创建空仓库(3分钟)

1. 登录 GitHub,点右上角 **+** → **New repository**
2. Repository name 填: `gpa-analyzer`
3. Description 填(会显示在仓库标题下,认真写):

   ```
   📊 成绩分析与GPA计算器 - 读取教务系统成绩单,自动计算GPA、分析学期趋势、生成可视化报告。支持多高校绩点规则配置。
   ```

4. 选 **Public**(公开,别人才能看到)
5. **下面三个框都不要勾**(不要 README、不要 .gitignore、不要 License——我们本地已经有了,勾了会冲突)
6. 点 **Create repository**

创建后 GitHub 会显示一页提示命令,先别管它,回到终端。

## 第 4 步:本地仓库初始化并推送(10分钟)

在终端执行(注意把 `你的用户名` 换成你的):

```bash
cd "C:\Users\lenovo\Documents\zcode 工作\gpa-analyzer"

# 初始化 Git 仓库(这个文件夹从此被 Git 跟踪)
git init

# 把项目文件加入暂存区(.gitignore 里列的会被自动排除)
git add .

# 检查一下哪些文件会被提交(output/ 和 __pycache__/ 不应该出现)
git status

# 做第一次提交,-m 后面是提交说明
git commit -m "初始提交:成绩分析与GPA计算器

- 读取CSV/Excel成绩单,自动计算GPA与加权平均分
- 支持多学校绩点规则(JSON配置化,内置4.0/5.0等预设)
- 生成学期趋势图、学分分布饼图、成绩雷达图
- 附带GitHub Actions持续集成"

# 关联你的 GitHub 远程仓库
git remote add origin https://github.com/你的用户名/gpa-analyzer.git

# 把 main 分支推送到 GitHub(-u 表示记住关联,以后直接 git push)
git push -u origin main
```

### 推送时需要登录怎么办?

2021 年起 GitHub 不能用密码推送,要用 **Personal Access Token(个人访问令牌)**:

1. 打开 https://github.com/settings/tokens
2. **Generate new token (classic)** → Note 随便写如 `my-laptop` → Expiration 选 `90 days` → 勾选 `repo` 权限 → **Generate token**
3. **立刻复制**(离开页面就看不到了)
4. 回到终端推送,弹窗里:用户名填 GitHub 用户名,密码**粘贴刚才的令牌**
5. Windows 会问是否记住凭据,选"是",以后就不用再输了

## 第 5 步:完善仓库门面(10分钟)

回到仓库网页刷新,应该能看到所有文件和 README 渲染出的漂亮主页。

1. **加 Topics 标签**(让项目可被搜索):仓库页面右侧齿轮 ⚙️ → Topics 添加:
   `python` `gpa-calculator` `education` `cli-app` `data-analysis` `matplotlib` `freshman-project`
2. **确认 CI 绿勾**:点顶部 **Actions** 标签页,能看到一次名叫 CI 的运行。等 1-2 分钟变绿 ✅ 说明自动测试通过。以后每次 push 都会自动跑
3. **(可选)加 CI 徽章**:仓库 Actions 页 → 点最新的 CI 运行 → 右侧 **Copy workflow badge URL** → 编辑 README.md,在标题下加一行:
   ```markdown
   ![CI](复制的URL)
   ```
   再提交推送一次(见第 6 步)

## 第 6 步:以后怎么更新代码(日常循环)

以后每次改了代码,三步走:

```bash
git add .                          # 1. 收集改动
git commit -m "说明这次改了什么"     # 2. 打包成一次提交
git push                           # 3. 推送到 GitHub
```

**提交说明要具体**(面试官会点开 commit 历史看):
- ✅ 好: `新增中国农业大学绩点规则配置` / `修复等级成绩无法识别的问题`
- ❌ 差: `更新` / `修改` / `fix`

## 第 7 步:写进简历

```
成绩分析与GPA计算器(Python) | 个人开源项目 | 2026.08 - 至今
· 独立开发命令行成绩分析工具,读取教务系统成绩单(CSV/Excel),计算GPA与加权平均分
· 设计配置化绩点规则系统,通过JSON配置支持不同高校的4.0/5.0等多种绩点制度
· 使用pandas进行多维度统计分析,matplotlib生成趋势图/饼图/雷达图可视化报告
· 配置GitHub Actions持续集成,自动验证各规则下程序可正常运行
· 开源地址: github.com/你的用户名/gpa-analyzer
```

面试时的话术:为什么做(自己的真实需求)→ 怎么设计(模块划分、配置化)→ 遇到什么问题怎么解决(列名不统一→别名映射;括号文件名→引号)→ 下一步计划(Web界面/更多学校)。

---

## 常见问题

**Q: push 报错 `rejected` / `non-fast-forward`?**
A: 多半是创建仓库时勾了 README。执行 `git pull origin main --rebase` 再 push。

**Q: 仓库里出现了 `output/` 或 `__pycache__/`?**
A: 说明 .gitignore 没生效就 add 过了。执行 `git rm -r --cached output __pycache__` 再 add/commit/push。

**Q: 想删掉重来?**
A: 删除文件夹里隐藏的 `.git` 文件夹(先在资源管理器"查看→显示隐藏项"),从第 4 步重新开始。远程仓库在 Settings 最底部可以删除。
