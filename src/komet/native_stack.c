#include <pthread.h>

static int booster_pthread_create(pthread_t *thread, const pthread_attr_t *attributes,
                                  void *(*start)(void *), void *argument) {
    if (attributes) {
        return pthread_create(thread, attributes, start, argument);
    }
    pthread_attr_t enlarged;
    int error = pthread_attr_init(&enlarged);
    if (error) return error;
    // GHC's default macOS worker stack is only 512 KiB.
    // ponytail: 64 MiB is finite; iterative LLVM serialization removes the depth limit.
    error = pthread_attr_setstacksize(&enlarged, 64 * 1024 * 1024);
    if (!error) error = pthread_create(thread, &enlarged, start, argument);
    pthread_attr_destroy(&enlarged);
    return error;
}

__attribute__((used)) static struct {
    const void *replacement;
    const void *original;
} interpose_pthread_create __attribute__((section("__DATA,__interpose"))) = {
    (const void *)booster_pthread_create, (const void *)pthread_create
};
