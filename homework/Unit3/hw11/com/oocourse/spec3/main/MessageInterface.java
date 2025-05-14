package com.oocourse.spec3.main;

public interface MessageInterface {
    /*@ public instance model int id;
      @ public instance model int socialValue;
      @ public instance model int type;
      @ public instance model non_null PersonInterface person1;
      @ public instance model nullable PersonInterface person2;
      @ public instance model nullable TagInterface tag;
      @*/

    //@ invariant person1!= null && !person1.equals(person2);

    //@ ensures \result == type;
    public /*@ pure @*/ int getType();

    //@ ensures \result == id;
    public /*@ pure @*/ int getId();

    //@ ensures \result == socialValue;
    public /*@ pure @*/ int getSocialValue();

    //@ ensures \result == person1;
    public /*@ pure @*/ PersonInterface getPerson1();

    /*@ requires person2 != null;
      @ ensures \result == person2;
      @*/
    public /*@ pure @*/ PersonInterface getPerson2();

    /*@ requires tag != null;
      @ ensures \result == tag;
      @*/
    public /*@ pure @*/ TagInterface getTag();

    /*@ public normal_behavior
      @ requires obj != null && obj instanceof MessageInterface;
      @ assignable \nothing;
      @ ensures \result == (((MessageInterface) obj).getId() == id);
      @ also
      @ public normal_behavior
      @ requires obj == null || !(obj instanceof MessageInterface);
      @ assignable \nothing;
      @ ensures \result == false;
      @*/
    public /*@ pure @*/ boolean equals(Object obj);
}
