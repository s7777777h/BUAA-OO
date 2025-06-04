package com.oocourse.spec3.exceptions;

import java.util.HashMap;

public class ErrorCount {
    private int count;
    private final HashMap<Integer, Integer> errorId;

    public ErrorCount() {
        count = 0;
        errorId = new HashMap<>();
    }

    public void putError(int id) {
        count++;
        if (errorId.containsKey(id)) {
            errorId.replace(id, errorId.get(id) + 1);
        } else {
            errorId.put(id, 1);
        }
    }

    public int getCount() {
        return count;
    }

    public int getIdCount(int id) {
        if (!errorId.containsKey(id)) {
            return 0;
        }
        return errorId.get(id);
    }
}
