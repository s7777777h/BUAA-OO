package com.oocourse.spec3.exceptions;

/**
 * {@code PathNotFoundException} 类用于表示在图中找不到从一个节点到另一个节点的路径时抛出的异常。
 * 该异常类包含两个整型参数 {@code id1} 和 {@code id2}，表示尝试查找路径的两个节点 ID。
 *
 * <p>异常统计信息的格式为：pnf-{@code x}, {@code id1}-{@code y1}, {@code id2}-{@code y2}，
 * 其中 {@code x} 为此类异常发生的总次数，{@code y1} 为 {@code id1} 触发此类异常的次数，
 * {@code y2} 为 {@code id2} 触发此类异常的次数。</p>
 */
public class PathNotFoundException extends Exception {
    private static final ErrorCount errorCount = new ErrorCount();
    private static int count = 0;
    private final int id1;
    private final int id2;

    /**
     * 构造一个新的 {@code PathNotFoundException} 实例。
     *
     * <p>该构造方法确保 {@code this.id1} 小于或等于 {@code this.id2}，并更新相应节点的错误计数。</p>
     *
     * @param id1 第一个节点 ID
     * @param id2 第二个节点 ID
     */
    public PathNotFoundException(int id1, int id2) {
        count++;

        if (id1 < id2) {
            this.id1 = id1;
            this.id2 = id2;
        } else {
            this.id1 = id2;
            this.id2 = id1;
        }

        if (id1 == id2) {
            errorCount.putError(id1);
        } else {
            errorCount.putError(id1);
            errorCount.putError(id2);
        }
    }

    /**
     * 输出异常的统计信息到标准输出。
     * 格式为：pnf-{@code x}, {@code id1}-{@code y1}, {@code id2}-{@code y2}，
     * 其中 {@code x} 为此类异常发生的总次数，{@code y1} 为 {@code id1} 触发此类异常的次数，
     * {@code y2} 为 {@code id2} 触发此类异常的次数。
     */
    public void print() {
        System.out.println("pnf-" + count
                + ", " + id1 + "-" + errorCount.getIdCount(id1)
                + ", " + id2 + "-" + errorCount.getIdCount(id2));
    }
}
