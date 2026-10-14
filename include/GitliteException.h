#ifndef GITLITE_EXCEPTION_H
#define GITLITE_EXCEPTION_H

#include <exception>
#include <string>

class GitliteException : public std::exception {
private:
    std::string message;

public:
    GitliteException();
    GitliteException(const std::string& msg);
    virtual const char* what() const noexcept override;
};

#endif // GITLITE_EXCEPTION_H
