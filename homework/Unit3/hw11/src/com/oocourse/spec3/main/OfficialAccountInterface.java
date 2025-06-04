package com.oocourse.spec3.main;

public interface OfficialAccountInterface {

    /*@ public instance model int ownerId;
      @ public instance model int id;
      @ public instance model non_null String name;
      @ public instance model non_null PersonInterface[] followers;
      @ public instance model non_null int[] articles;
      @ public instance model non_null int[] contributions;
      @*/

    /*@ invariant followers != null && articles != null && contributions != null && followers.length == contributions.length &&
      @  (\forall int i,j; 0 <= i && i < j && j < followers.length;
      @   !followers[i].equals(followers[j])) &&
      @  (\forall int i,j; 0 <= i && i < j && j < articles.length;
      @   articles[i] != articles[j]);
      @*/

    //@ ensures \result == ownerId;
    public /*@ pure @*/ int getOwnerId();

    /*@ public normal_behavior
      @ requires !containsFollower(person);
      @ assignable followers, contributions;
      @ ensures containsFollower(person);
      @ ensures (\exists int i; 0 <= i && i < followers.length; followers[i].getId() == person.getId() && contributions[i] == 0);
      @*/
    public /*@ safe @*/ void addFollower(/*@ non_null @*/PersonInterface person);

    //@ ensures \result == (\exists int i; 0 <= i && i < followers.length; followers[i].getId() == person.getId());
    public /*@ pure @*/ boolean containsFollower(PersonInterface person);

    /*@ public normal_behavior
      @ requires !containsArticle(id);
      @ assignable articles, contributions;
      @ ensures containsArticle(id) &&
      @         (\exists int i; 0 <= i && i < followers.length; followers[i] == person && contributions[i] == \old(contributions[i]) + 1);
      @*/
    public /*@ safe @*/ void addArticle(/*@ non_null @*/PersonInterface person, int id);

    //@ ensures \result == (\exists int i; 0 <= i && i < articles.length; articles[i] == id);
    public /*@ pure @*/ boolean containsArticle(int id);

    /*@ public normal_behavior
      @ requires containsArticle(id);
      @ assignable articles;
      @ ensures !containsArticle(id);
      @*/
    public /*@ safe @*/ void removeArticle(int id);
    
    /*@ public normal_behavior
      @ assignable \nothing;
      @ ensures (\result == (\min int bestId;
      @                         (\exists int i; 0 <= i && i < followers.length; followers[i].id == bestId &&
      @                             (\forall int j; 0 <= j && j < followers.length; contributions[i] >= contributions[j]));
      @                         bestId));
     */
    public /*@ pure @*/ int getBestContributor();

}
