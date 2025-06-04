package com.oocourse.spec3.exceptions;

/**
 * {@code EqualTagIdException} 类用于表示当不满足标签 ID 唯一性要求时抛出的异常。
 * 该异常类包含一个整型参数 {@code id}，表示触发异常的 tag 的 ID。
 *
 * <p>异常统计信息的格式为：eti-{@code x}, {@code id}-{@code y}，
 * 其中 {@code x} 为此类异常发生的总次数，{@code y} 为该 {@code id} 触发此类异常的次数。</p>
 */
public class EqualTagIdException extends Exception {
    private static final ErrorCount errorCount = new ErrorCount();
    private final int id;

    /**
     * 构造一个新的 {@code EqualTagIdException} 实例。
     *
     * @param id 触发异常的 tag ID
     */
    public EqualTagIdException(int id) {
        this.id = id;
        errorCount.putError(id);
    }

    /**
     * 输出异常的统计信息到标准输出。
     * 格式为：eti-{@code x}, {@code id}-{@code y}，其中 {@code x} 为此类异常发生的总次数，
     * {@code y} 为该 {@code id} 触发此类异常的次数。
     */
    public void print() {
        System.out.println("eti-" + errorCount.getCount() +
                ", " + id + "-" + errorCount.getIdCount(id));
    }
}
