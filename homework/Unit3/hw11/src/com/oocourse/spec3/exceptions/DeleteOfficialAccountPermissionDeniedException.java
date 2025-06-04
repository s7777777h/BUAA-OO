package com.oocourse.spec3.exceptions;

/**
 * {@code DeleteOfficialAccountPermissionDeniedException} 类用于表示尝试删除公众号时权限不足的异常。
 * 该异常类包含两个整型参数 {@code id1} 和 {@code id2}，分别表示尝试删除公众号的人员 ID 和其尝试删除的公众号 ID。
 *
 * <p>异常统计信息的格式为：doapd-{@code x}, {@code id1}-{@code y1}, {@code id2}-{@code y2}，
 * 其中 {@code x} 为此类异常发生的总次数，{@code y1} 为 {@code id1} 触发此类异常的次数，
 * {@code y2} 为 {@code id2} 触发此类异常的次数。</p>
 */
public class DeleteOfficialAccountPermissionDeniedException extends Exception {
    private static final ErrorCount errorCount = new ErrorCount();
    private static int count = 0;
    private final int id1;
    private final int id2;
    
    /**
     * 构造一个新的 {@code DeleteOfficialAccountPermissionDeniedException} 实例。
     *
     * <p>该构造方法会根据 {@code id1} 和 {@code id2} 的大小来确保 {@code this.id1} 小于或等于 {@code this.id2}，
     * 并更新相应节点的错误计数。</p>
     *
     * @param id1 尝试删除公众号的人员 ID
     * @param id2 本次尝试删除的公众号 ID
     */
    public DeleteOfficialAccountPermissionDeniedException(int id1, int id2) {
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
     * 格式为：doapd-{@code x}, {@code id1}-{@code y1}, {@code id2}-{@code y2}，
     * 其中 {@code x} 为此类异常发生的总次数，{@code y1} 为 {@code id1} 触发此类异常的次数，
     * {@code y2} 为 {@code id2} 触发此类异常的次数。
     */
    public void print() {
        System.out.println("doapd-" + count
                + ", " + id1 + "-" + errorCount.getIdCount(id1)
                + ", " + id2 + "-" + errorCount.getIdCount(id2));
    }
}
