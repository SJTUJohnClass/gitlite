#ifndef SOME_OBJ_H
#define SOME_OBJ_H

#include <string>

// main.cpp 的命令门面。main.cpp 不可修改，故本类声明不可改动；
// 请在 src/SomeObj.cpp 中实现各命令，具体逻辑建议拆分到自行设计的类中。
class SomeObj {
public:
    SomeObj();

    void init();                        // gitlite init
    void add(const std::string& f);     // gitlite add [文件名]
    void commit(const std::string& m);  // gitlite commit [提交信息]
    void rm(const std::string& f);      // gitlite rm [文件名]
    void log();                         // gitlite log
    void globalLog();                   // gitlite global-log
    void listTags();                    // gitlite tag
    void tag(const std::string& n);     // gitlite tag [标签名]
    void tag(const std::string& n,
             const std::string& rev);   // gitlite tag [标签名] [revision]
    void status();                      // gitlite status

    void checkoutBranch(const std::string& b);                      // gitlite checkout [分支名]
    void checkoutFile(const std::string& f);                        // gitlite checkout -- [文件名]
    void checkoutFileInCommit(const std::string& rev,
                              const std::string& f);                // gitlite checkout [revision] -- [文件名]

    void branch(const std::string& b);  // gitlite branch [分支名]
    void rmBranch(const std::string& b);// gitlite rm-branch [分支名]
    void reset(const std::string& rev); // gitlite reset [revision]
    void merge(const std::string& b);   // gitlite merge [分支名]

    void addRemote(const std::string& n, const std::string& p);     // gitlite add-remote [远程名] [路径]/.gitlite
    void rmRemote(const std::string& n);                            // gitlite rm-remote [远程名]
    void push(const std::string& n, const std::string& b);          // gitlite push [远程名] [远程分支名]
    void fetch(const std::string& n, const std::string& b);         // gitlite fetch [远程名] [远程分支名]
    void pull(const std::string& n, const std::string& b);          // gitlite pull [远程名] [远程分支名]

    void diff();                                                    // gitlite diff
    void diffWithCommit(const std::string& rev);                    // gitlite diff [revision]
    void diffBetween(const std::string& rev1, const std::string& rev2);// gitlite diff [revision1] [revision2]
    void show();                                                    // gitlite show
    void show(const std::string& rev);                              // gitlite show [revision]
};

#endif // SOME_OBJ_H
