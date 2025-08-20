#ifndef UTILS_H
#define UTILS_H

#include <string>
#include <vector>
#include <fstream>
#include <iostream>
#include <sstream>
#include <algorithm>
#include <dirent.h>
#include <sys/stat.h>
#include <unistd.h>
#include <cstdint>
#include <iomanip>

namespace SHA1 {
    class SHA {
    private:
        typedef uint8_t BYTE;
        typedef uint32_t WORD;
        WORD A, B, C, D, E;
        std::vector<WORD> Word;
        void reset();
        std::string padding(std::string message);
        inline WORD charToWord(char ch);
        WORD shiftLeft(WORD x, int n);
        WORD kt(int t);
        WORD ft(int t, WORD B, WORD C, WORD D);
        void getWord(std::string& message, int index);
    public:
        SHA();
        std::string sha(std::string message);
    };
    extern SHA sha;
    std::string sha1(std::string message);
    std::string sha1(std::string s1, std::string s2);
    std::string sha1(std::string s1, std::string s2, std::string s3, std::string s4);
}

class Utils {
public:
    static const int UID_LENGTH = 40;

    // SHA-1 hash functions
    static std::string sha1(const std::string& s1);
    static std::string sha1(const std::string& s1, const std::string& s2);
    static std::string sha1(const std::string& s1, const std::string& s2, 
                          const std::string& s3, const std::string& s4);
    static std::string sha1(const std::vector<unsigned char>& data);

    // File operations
    static bool restrictedDelete(const std::string& filepath);
    static std::vector<unsigned char> readContents(const std::string& filepath);
    static std::string readContentsAsString(const std::string& filepath);
    static void writeContents(const std::string& filepath, const std::string& content);
    static void writeContents(const std::string& filepath, const std::vector<unsigned char>& content);

    // Directory operations
    static std::vector<std::string> plainFilenamesIn(const std::string& dirPath);
    static std::string join(const std::string& first, const std::string& second);
    static std::string join(const std::string& first, const std::string& second, const std::string& third);

    // Serialization (simplified for basic types)
    static std::vector<unsigned char> serialize(const std::string& obj);

    // Message and error reporting
    static void message(const std::string& msg);
    static void exitWithMessage(const std::string& msg);

    // File existence check
    static bool exists(const std::string& path);
    static bool isFile(const std::string& path);
    static bool isDirectory(const std::string& path);
    static bool createDirectories(const std::string& path);
};

#endif // UTILS_H
