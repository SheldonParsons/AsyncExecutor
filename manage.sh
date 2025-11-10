#!/bin/bash

# --- 变量定义 ---
# 你的服务名称 (必须和 .service 文件名一致)
SERVICE_NAME="AsyncExecutor"

# 获取脚本所在的目录 (即项目根目录)
# (这要求 manage.sh 必须在项目根目录)
PROJECT_DIR=$(cd "$(dirname "$0")" && pwd)

# 源 .service 文件路径 (在你的项目中)
SOURCE_SERVICE_FILE="$PROJECT_DIR/$SERVICE_NAME.service"

# 目标 systemd 目录 (这是 Linux 系统的标准路径)
SYSTEMD_PATH="/etc/systemd/system"

# 目标 .service 文件路径
DEST_SERVICE_FILE="$SYSTEMD_PATH/$SERVICE_NAME.service"

# 日志文件路径 (必须和 log_config.json 中的 "filename" 一致)
LOG_FILE="$PROJECT_DIR/log/app.log"


# --- 函数定义 ---
# ( $1 是传入的第一个参数，比如 "start", "stop" )
case "$1" in
  install)
    echo "--- 正在安装服务 $SERVICE_NAME ---"

    # 1. 复制 .service 文件到 systemd 目录
    #    (使用 sudo 是因为 /etc/ 目录需要 root 权限)
    echo "正在复制 $SOURCE_SERVICE_FILE 到 $DEST_SERVICE_FILE"
    sudo cp $SOURCE_SERVICE_FILE $DEST_SERVICE_FILE

    # 2. 重新加载 systemd 配置，使其识别新文件
    echo "正在重新加载 systemd daemon..."
    sudo systemctl daemon-reload

    # 3. 设置服务开机自启
    echo "正在设置服务开机自启..."
    sudo systemctl enable $SERVICE_NAME

    echo "--- 安装完成. ---"
    echo "你可以运行 './manage.sh start' 来启动服务."
    ;;

  uninstall)
    echo "--- 正在卸载服务 $SERVICE_NAME ---"

    # 1. 停止服务 (如果正在运行)
    sudo systemctl stop $SERVICE_NAME

    # 2. 取消开机自启
    sudo systemctl disable $SERVICE_NAME

    # 3. 删除 .service 文件
    echo "正在删除 $DEST_SERVICE_FILE"
    sudo rm $DEST_SERVICE_FILE

    # 4. 重新加载 systemd 配置
    echo "正在重新加载 systemd daemon..."
    sudo systemctl daemon-reload

    echo "--- 卸载完成. ---"
    ;;

  start)
    echo "--- 正在启动服务 $SERVICE_NAME ---"
    sudo systemctl start $SERVICE_NAME
    echo "--- 启动完成. ---"
    echo "请运行 './manage.sh status' 查看状态."
    ;;

  stop)
    echo "--- 正在停止服务 $SERVICE_NAME ---"
    sudo systemctl stop $SERVICE_NAME
    echo "--- 停止完成. ---"
    ;;

  restart)
    echo "--- 正在重启服务 $SERVICE_NAME ---"
    sudo systemctl restart $SERVICE_NAME
    echo "--- 重启完成. ---"
    ;;

  status)
    echo "--- 正在查看服务 $SERVICE_NAME 状态 ---"
    systemctl status $SERVICE_NAME
    ;;

  logs)
    echo "--- 正在实时查看日志 (按 Ctrl+C 退出) ---"
    tail -f $LOG_FILE
    ;;

  *)
    # 默认帮助信息
    echo "用法: $0 {install|uninstall|start|stop|restart|status|logs}"
    echo "  install   : [首次运行] 安装服务并设置开机自启."
    echo "  uninstall : 卸载服务."
    echo "  start     : 启动服务."
    echo "  stop      : 停止服务."
    echo "  restart   : 重启服务."
    echo "  status    : 查看服务运行状态."
    echo "  logs      : 实时查看 app.log 文件."
    exit 1
    ;;
esac

exit 0