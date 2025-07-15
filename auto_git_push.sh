#!/bin/bash

# 定义提交信息，默认为 "Auto commit"
COMMIT_MSG=${1:-"Auto commit"}

# 遍历当前目录及其子目录，查找所有的 Git 仓库
find . -type d -name ".git" | while read -r git_dir; do
    # 获取 Git 仓库的根目录
    repo_dir=$(dirname "$git_dir")
    cd "$repo_dir" || continue

    echo "正在处理仓库: $repo_dir"

    # 获取远程仓库地址
    remote_url=$(git remote get-url origin)
    echo "  远程仓库地址: $remote_url"

    # 检查是否有文件变更
    if [ -z "$(git status --porcelain)" ]; then
        echo "  此仓库没有文件变更，无需提交。"
        cd - > /dev/null
        continue
    fi

    # 添加所有更改到暂存区
    git add .

    # 提交更改到本地仓库
    git commit -m "$COMMIT_MSG"

    # 获取当前分支名
    current_branch=$(git branch --show-current)

    # 拉取远程仓库的最新更改并合并
    git pull --rebase origin "$current_branch"

    # 处理合并冲突（如果有）
    if [ $? -ne 0 ]; then
        echo "  合并过程中出现冲突，请手动解决冲突后再次运行脚本。"
        cd - > /dev/null
        continue
    fi

    # 推送本地仓库的更改到远程仓库
    git push origin "$current_branch"

    # 检查推送是否成功
    if [ $? -eq 0 ]; then
        echo "  此仓库代码已成功推送到远程仓库。"
    else
        echo "  此仓库推送失败，请检查网络连接或权限设置。"
    fi

    cd - > /dev/null
done