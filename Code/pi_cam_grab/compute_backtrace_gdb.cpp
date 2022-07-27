#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>
#include <unistd.h>
#include <sys/prctl.h>
#include <iostream>
#include <limits.h>
#include <fmt/core.h>

#include "compute_backtrace_gdb.h"

std::string get_selfpath() {
    char buf[PATH_MAX];
    int len = readlink("/proc/self/exe", buf, sizeof(buf)-1);
    if (len == -1) {
        throw std::runtime_error(fmt::format("readlink /proc/self/exe failed with errno={}", errno));
    }
    return std::string(buf, len);
}

std::string compute_backtrace_gdb() {
    std::string pid_str = fmt::format("{}", getpid()).c_str();
    prctl(PR_SET_PTRACER, PR_SET_PTRACER_ANY, 0, 0, 0);

    int pipe_fds[2];
    pipe(pipe_fds);
    int pipe_read_fd = pipe_fds[0];
    int pipe_write_fd = pipe_fds[1];

    int child_pid = fork();
    if (!child_pid) {
        dup2(pipe_write_fd, 1); // replace stdout with pipe_write
        dup2(pipe_write_fd, 2); // replace stderr with pipe_write
        close(pipe_read_fd);
        close(pipe_write_fd);
        execl("/usr/bin/gdb", "gdb", "--batch", "-n", "-ex", "thread", "-ex", "bt", get_selfpath().c_str(), pid_str.c_str(), NULL);
        std::cerr << "ERROR: failed to execl /usr/bin/gdb\n";
        abort(); /* If gdb failed to start */
    } else {
        close(pipe_write_fd);
        std::string ret;
        char buf[512];
        while (1) {
            int len = read(pipe_read_fd, buf, sizeof(buf));
            if (len <= 0) break;
            ret += std::string(buf, len);
        }
        waitpid(child_pid,NULL,0);
        return ret;
    }
}
