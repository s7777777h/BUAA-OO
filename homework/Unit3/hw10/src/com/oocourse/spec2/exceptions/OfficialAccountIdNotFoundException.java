package com.oocourse.spec2.exceptions;

/**
 * {@code OfficialAccountIdNotFoundException} 类用于表示当尝试访问不存在的公众号 ID 时抛出的异常。
 * 该异常类包含一个整型参数 {@code id}，表示触发异常的不存在公众号 ID。
 *
 * <p>异常统计信息的格式为：oainf-{@code x}, {@code id}-{@code y}，其中 {@code x} 为此类异常发生的总次数，
 * {@code y} 为该 {@code id} 触发此类异常的次数。</p>
 */
public class OfficialAccountIdNotFoundException extends Exception {
    private static final ErrorCount errorCount = new ErrorCount();
    private final int id;

    /**
     * 构造一个新的 {@code OfficialAccountIdNotFoundException} 实例。
     *
     * @param id 触发异常的不存在公众号 ID
     */
    public OfficialAccountIdNotFoundException(int id) {
        this.id = id;
        errorCount.putError(id);
    }

    /**
     * 输出异常的统计信息到标准输出。
     * 格式为：oainf-{@code x}, {@code id}-{@code y}，其中 {@code x} 为此类异常发生的总次数，
     * {@code y} 为该 {@code id} 触发此类异常的次数。
     */
    public void print() {
        System.out.println("oainf-" + errorCount.getCount() +
                ", " + id + "-" + errorCount.getIdCount(id));
    }
}
