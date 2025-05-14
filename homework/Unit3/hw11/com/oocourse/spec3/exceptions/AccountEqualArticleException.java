package com.oocourse.spec3.exceptions;

public class AccountEqualArticleException extends Exception {

    private final int id;
    private final String name;
    private final String method;

    /**
     * 构造一个新的AccountEqualArticleException实例
     *
     * @param id 重复article的ID
     * @param name 触发异常的公众号名字
     * @param method 触发异常的方法名
     */

    public AccountEqualArticleException(int id, String name, String method) {
        this.id = id;
        this.name = name;
        this.method = method;
    }

    public int getId() {
        return id;
    }

    public String getName() {
        return name;
    }

    public String getMethod() {
        return method;
    }

    @Override
    public String toString() {
        return " due to " + name + " " + method;
    }
}
