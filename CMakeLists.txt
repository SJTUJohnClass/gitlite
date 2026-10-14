cmake_minimum_required(VERSION 3.10)
project(gitlite LANGUAGES CXX)

# TODO: 请在此处自行完成项目的编译配置。
#
# 要求：
# 1. 在 build/ 中创建一个名称为 gitlite 的可执行目标；
# 2. 将 main.cpp 和所有需要的实现文件加入该目标；
# 3. 自行设置所需的 C++ 标准、头文件目录和编译选项。


# ==================== ACMOJ 配置（请勿删除）====================
# ACMOJ 的 Git 评测会从仓库根目录读取名为 code 的编译产物。
# 上方必须已经通过 add_executable(gitlite ...) 创建 gitlite 目标。
add_custom_command(
    TARGET gitlite POST_BUILD
    COMMAND "${CMAKE_COMMAND}" -E copy_if_different
            "$<TARGET_FILE:gitlite>"
            "${CMAKE_SOURCE_DIR}/code"
    COMMENT "Copying gitlite executable to ACMOJ artifact: code"
    VERBATIM
)
# ================== ACMOJ 配置结束（请勿删除）==================
