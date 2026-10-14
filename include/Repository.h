#ifndef REPOSITORY_H
#define REPOSITORY_H

#include <string>

// 建议类：抽象仓库的持久化状态，包括 HEAD、分支、标签、暂存区与对象库；
// 可自由扩充或重新设计。
// 注意：main.cpp 的 checkCWD 依赖 getGitliteDir()，请保留该方法。
class Repository {
public:
    // 元数据目录名，即 ".gitlite"
    static std::string getGitliteDir();
};

#endif // REPOSITORY_H
