package com.oocourse.spec3.exceptions;

/**
 * {@code EqualArticleIdException} 类用于表示当不满足文章 ID 唯一性要求时抛出的异常。
 * 该异常类包含一个整型参数 {@code id}，表示触发异常的具体文章 ID。
 *
 * <p>异常统计信息的格式为：eai-{@code x}, {@code id}-{@code y}，其中 {@code x} 为此类异常发生的总次数，
 * {@code y} 为该 {@code id} 触发此类异常的次数。</p>
 */
public class EqualArticleIdException extends Exception {
    private static final ErrorCount errorCount = new ErrorCount();
    private final int id;

    /**
     * 构造一个新的 {@code EqualArticleIdException} 实例。
     *
     * @param id 触发异常的文章 ID
     */
    public EqualArticleIdException(int id) {
        this.id = id;
        errorCount.putError(id);
    }

    /**
     * 输出异常的统计信息到标准输出。
     * 格式为：eai-{@code x}, {@code id}-{@code y}，其中 {@code x} 为此类异常发生的总次数，
     * {@code y} 为该 {@code id} 触发此类异常的次数。
     */
    public void print() {
        System.out.println("eai-" + errorCount.getCount() + ", "
                + id + "-" + errorCount.getIdCount(id));
    }
}
