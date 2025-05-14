package com.oocourse.spec3.main;

public interface RedEnvelopeMessageInterface extends MessageInterface {
    //@ public instance model int money;

    //@ public invariant socialValue == money * 5;

    //@ ensures \result == money;
    public /*@ pure @*/ int getMoney();
}
