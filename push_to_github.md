# 推送到GitHub指南

## 方法1：通过GitHub网页创建并推送

1. **创建GitHub仓库**
   - 访问 https://github.com
   - 点击右上角的 "+" → "New repository"
   - 仓库名称：`Anamind`
   - 描述：`Flask WeChat chat record analysis application`
   - 选择 Public 或 Private
   - 不要勾选 "Initialize this repository with a README"
   - 点击 "Create repository"

2. **推送到GitHub**
   ```bash
   git remote add origin https://github.com/您的用户名/Anamind.git
   git branch -M main
   git push -u origin main
   ```

## 方法2：使用GitHub CLI（如果已安装）

```bash
gh repo create Anamind --public --description="Flask WeChat chat record analysis application"
git remote add origin https://github.com/您的用户名/Anamind.git
git branch -M main
git push -u origin main
```

## 注意事项

- 将 `您的用户名` 替换为实际的GitHub用户名
- 确保您已登录GitHub账户
- 如果选择私有仓库，只有您和授权用户可以访问

推送完成后，您的Flask应用就保存在GitHub的Anamind仓库中了！