package com.oocourse.spec3.exceptions;

/**
 * {@code RelationNotFoundException} 类用于表示当查找的关系不存在时抛出的异常。
 * 该异常类包含两个整型参数 {@code id1} 和 {@code id2}，分别代表触发异常时
 * 不存在的关系联系的具体人员 ID。
 *
 * <p>异常统计信息的格式为：rnf-{@code x}, {@code id1}-{@code y}, {@code id2}-{@code z}，
 * 其中 {@code x} 为此类异常发生的总次数，{@code y} 为 {@code id1} 触发此类异常的次数，
 * {@code z} 为 {@code id2} 触发此类异常的次数。</p>
 */
public class RelationNotFoundException extends Exception {
    private static final ErrorCount errorCount = new ErrorCount();
    private final int id1;
    private final int id2;

    /**
     * 构造一个新的 {@code RelationNotFoundException} 实例。
     *
     * <p>该构造方法将确保 {@code this.id1} 小于或等于 {@code this.id2}，并更新这两个 ID 的错误计数。</p>
     *
     * @param id1 触发异常的人员 ID
     * @param id2 触发异常的人员 ID
     */
    public RelationNotFoundException(int id1, int id2) {
        if (id1 < id2) {
            this.id1 = id1;
            this.id2 = id2;
        } else {
            this.id1 = id2;
            this.id2 = id1;
        }
        errorCount.putError(id1);
        errorCount.putError(id2);
    }

    /**
     * 输出异常的统计信息到标准输出。
     * 格式为：rnf-{@code x}, {@code id1}-{@code y}, {@code id2}-{@code z}，
     * 其中 {@code x} 为此类异常发生的总次数，{@code y} 为 {@code id1} 触发此类异常的次数，
     * {@code z} 为 {@code id2} 触发此类异常的次数。
     */
    public void print() {
        System.out.println("rnf-" + errorCount.getCount() / 2 +
                ", " + id1 + "-" + errorCount.getIdCount(id1) +
                ", " + id2 + "-" + errorCount.getIdCount(id2));
    }
}
