package com.oocourse.spec3.main;

import com.oocourse.spec3.exceptions.*;

import java.util.List;

public interface NetworkInterface {

    /*@ public instance model non_null PersonInterface[] persons;
      @ public instance model non_null OfficialAccountInterface[] accounts;
      @ public instance model non_null int[] articles;
      @ public instance model non_null int[] articleContributors;
      @ public instance model non_null MessageInterface[] messages;
      @ public instance model non_null int[] emojiIdList;
      @ public instance model non_null int[] emojiHeatList;
      @*/

    /*@ invariant persons != null && accounts != null && articles != null && articleContributors != null && articles.length == articleContributors.length &&
      @ (\forall int i,j; 0 <= i && i < j && j < persons.length;
      @           !persons[i].equals(persons[j])) &&
      @ (\forall int i,j; 0 <= i && i < j && j < accounts.length;
      @           accounts[i] != accounts[j]) &&
      @ (\forall int i,j; 0 <= i && i < j && j < articles.length;
      @           articles[i] != articles[j]) &&
      @ messages != null && (\forall int i,j; 0 <= i && i < j && j < messages.length;
      @           !messages[i].equals(messages[j])) &&
      @ emojiIdList != null && emojiHeatList != null &&
      @ (\forall int i,j; 0 <= i && i < j && j < emojiIdList.length;
      @           emojiIdList[i] != emojiIdList[j]) &&
      @ emojiIdList.length == emojiHeatList.length;
      @ */

    //@ ensures \result == (\exists int i; 0 <= i && i < persons.length; persons[i].getId() == id);
    public /*@ pure @*/ boolean containsPerson(int id);

    /*@ public normal_behavior
      @ requires containsPerson(id);
      @ ensures (\exists int i; 0 <= i && i < persons.length; persons[i].getId() == id &&
      @         \result == persons[i]);
      @ also
      @ public normal_behavior
      @ requires !containsPerson(id);
      @ ensures \result == null;
      @*/
    public /*@ pure @*/ PersonInterface getPerson(int id);

    /*@ public normal_behavior
      @ requires !containsPerson(person.getId());
      @ assignable persons;
      @ ensures containsPerson(person.getId());
      @ also
      @ public exceptional_behavior
      @ signals (EqualPersonIdException e) containsPerson(person.getId());
      @*/
    public /*@ safe @*/ void addPerson(/*@ non_null @*/PersonInterface person) throws EqualPersonIdException;

    /*@ public normal_behavior
      @ requires containsPerson(id1) &&
      @          containsPerson(id2) &&
      @          !getPerson(id1).isLinked(getPerson(id2));
      @ assignable persons[*];
      @ ensures getPerson(id1).isLinked(getPerson(id2)) &&
      @         getPerson(id2).isLinked(getPerson(id1));
      @ ensures getPerson(id1).queryValue(getPerson(id2)) == value;
      @ ensures getPerson(id2).queryValue(getPerson(id1)) == value;
      @ also
      @ public exceptional_behavior
      @ assignable \nothing;
      @ requires !containsPerson(id1) ||
      @          !containsPerson(id2) ||
      @          getPerson(id1).isLinked(getPerson(id2));
      @ signals (PersonIdNotFoundException e) !containsPerson(id1);
      @ signals (PersonIdNotFoundException e) containsPerson(id1) &&
      @                                       !containsPerson(id2);
      @ signals (EqualRelationException e) containsPerson(id1) &&
      @                                    containsPerson(id2) &&
      @                                    getPerson(id1).isLinked(getPerson(id2));
      @*/
    public /*@ safe @*/ void addRelation(int id1, int id2, int value) throws
            PersonIdNotFoundException, EqualRelationException;

    /*@ public normal_behavior
      @ requires containsPerson(id1) &&
      @          containsPerson(id2) &&
      @          id1 != id2 &&
      @          getPerson(id1).isLinked(getPerson(id2)) &&
      @          getPerson(id1).queryValue(getPerson(id2)) + value > 0;
      @ assignable persons[*];
      @ ensures getPerson(id1).isLinked(getPerson(id2)) &&
      @         getPerson(id2).isLinked(getPerson(id1));
      @ ensures getPerson(id1).queryValue(getPerson(id2)) == \old(getPerson(id1).queryValue(getPerson(id2))) + value;
      @ ensures getPerson(id2).queryValue(getPerson(id1)) == \old(getPerson(id2).queryValue(getPerson(id1))) + value;
      @ also
      @ public normal_behavior
      @ requires containsPerson(id1) &&
      @          containsPerson(id2) &&
      @          id1 != id2 &&
      @          getPerson(id1).isLinked(getPerson(id2)) &&
      @          getPerson(id1).queryValue(getPerson(id2)) + value <= 0;
      @ assignable persons[*];
      @ ensures  !getPerson(id1).isLinked(getPerson(id2)) &&
      @          !getPerson(id2).isLinked(getPerson(id1));
      @ ensures  getPerson(id1).value.length == getPerson(id1).acquaintance.length;
      @ ensures  getPerson(id2).value.length == getPerson(id2).acquaintance.length;
      @ ensures  (\forall int i; 0 <= i && i < getPerson(id1).tags.length;
      @                      \old(getPerson(id1).tags[i].hasPerson(getPerson(id2)))==>!getPerson(id1).tags[i].hasPerson(getPerson(id2)));
      @ ensures  (\forall int i; 0 <= i && i < getPerson(id2).tags.length;
      @                      \old(getPerson(id2).tags[i].hasPerson(getPerson(id1)))==>!getPerson(id2).tags[i].hasPerson(getPerson(id1)));
      @ also
      @ public exceptional_behavior
      @ requires !containsPerson(id1) ||
      @          !containsPerson(id2) ||
      @          id1 == id2 ||
      @          !getPerson(id1).isLinked(getPerson(id2));
      @ signals (PersonIdNotFoundException e) !containsPerson(id1);
      @ signals (PersonIdNotFoundException e) containsPerson(id1) &&
      @                                       !containsPerson(id2);
      @ signals (EqualPersonIdException e) containsPerson(id1) &&
      @                                    containsPerson(id2) &&
      @                                    id1 == id2;
      @ signals (RelationNotFoundException e) containsPerson(id1) &&
      @                                       containsPerson(id2) &&
      @                                       id1 != id2 &&
      @                                       !getPerson(id1).isLinked(getPerson(id2));
      @*/
    public /*@ safe @*/ void modifyRelation(int id1, int id2, int value) throws PersonIdNotFoundException,
            EqualPersonIdException, RelationNotFoundException;

    /*@ public normal_behavior
      @ requires containsPerson(id1) &&
      @          containsPerson(id2) &&
      @          getPerson(id1).isLinked(getPerson(id2));
      @ assignable \nothing;
      @ ensures \result == getPerson(id1).queryValue(getPerson(id2));
      @ also
      @ public exceptional_behavior
      @ signals (PersonIdNotFoundException e) !containsPerson(id1);
      @ signals (PersonIdNotFoundException e) containsPerson(id1) &&
      @                                       !containsPerson(id2);
      @ signals (RelationNotFoundException e) containsPerson(id1) &&
      @                                       containsPerson(id2) &&
      @                                       !getPerson(id1).isLinked(getPerson(id2));
      @*/
    public /*@ pure @*/ int queryValue(int id1, int id2) throws
            PersonIdNotFoundException, RelationNotFoundException;

    /*@ public normal_behavior
      @ requires containsPerson(id1) &&
      @          containsPerson(id2);
      @ assignable \nothing;
      @ ensures \result == (\exists PersonInterface[] array; array.length >= 2;
      @                     array[0].equals(getPerson(id1)) &&
      @                     array[array.length - 1].equals(getPerson(id2)) &&
      @                      (\forall int i; 0 <= i && i < array.length - 1;
      @                      array[i].isLinked(array[i + 1])));
      @ also
      @ public exceptional_behavior
      @ signals (PersonIdNotFoundException e) !containsPerson(id1);
      @ signals (PersonIdNotFoundException e) containsPerson(id1) &&
      @                                       !containsPerson(id2);
      @*/
    public /*@ pure @*/ boolean isCircle(int id1, int id2) throws PersonIdNotFoundException;

    /*@ ensures \result ==
      @         (\sum int i; 0 <= i && i < persons.length;
      @             (\sum int j; i < j && j < persons.length;
      @                 (\sum int k; j < k && k < persons.length
      @                     && getPerson(persons[i].getId()).isLinked(getPerson(persons[j].getId()))
      @                     && getPerson(persons[j].getId()).isLinked(getPerson(persons[k].getId()))
      @                     && getPerson(persons[k].getId()).isLinked(getPerson(persons[i].getId()));
      @                     1)));
      @*/
    public /*@ pure @*/ int queryTripleSum();

    /*@ public normal_behavior
      @ requires containsPerson(personId) &&
      @          !getPerson(personId).containsTag(tag.getId());
      @ assignable getPerson(personId).tags;
      @ ensures getPerson(personId).containsTag(tag.getId());
      @ also
      @ public exceptional_behavior
      @ signals (PersonIdNotFoundException e) !containsPerson(personId);
      @ signals (EqualTagIdException e) containsPerson(personId) &&
      @                                 getPerson(personId).containsTag(tag.getId());
      @*/
    public /*@ safe @*/ void addTag(int personId,/*@ non_null @*/TagInterface tag) throws PersonIdNotFoundException, EqualTagIdException;

    /*@ public normal_behavior
      @ requires containsPerson(personId1) &&
      @          containsPerson(personId2) &&
      @          personId1!=personId2      &&
      @          getPerson(personId2).isLinked(getPerson(personId1)) &&
      @          getPerson(personId2).containsTag(tagId) &&
      @          !getPerson(personId2).getTag(tagId).hasPerson(getPerson(personId1)) &&
      @          getPerson(personId2).getTag(tagId).persons.length <= 999;
      @ assignable getPerson(personId2).getTag(tagId).persons;
      @ ensures getPerson(personId2).getTag(tagId).hasPerson(getPerson(personId1));
      @ also
      @ public normal_behavior
      @ requires containsPerson(personId1) &&
      @          containsPerson(personId2) &&
      @          personId1!=personId2      &&
      @          getPerson(personId2).isLinked(getPerson(personId1)) &&
      @          getPerson(personId2).containsTag(tagId) &&
      @          !getPerson(personId2).getTag(tagId).hasPerson(getPerson(personId1)) &&
      @          getPerson(personId2).getTag(tagId).persons.length > 999;
      @ assignable \nothing
      @ also
      @ public exceptional_behavior
      @ signals (PersonIdNotFoundException e) !containsPerson(personId1);
      @ signals (PersonIdNotFoundException e) containsPerson(personId1) &&
      @                                       !containsPerson(personId2);
      @ signals (EqualPersonIdException e)    containsPerson(personId1) &&
      @                                       containsPerson(personId2) &&
      @                                       personId1==personId2 ;
      @ signals (RelationNotFoundException e) containsPerson(personId1) &&
      @                                       containsPerson(personId2) &&
      @                                       personId1!=personId2      &&
      @                                       !getPerson(personId2).isLinked(getPerson(personId1));
      @ signals (TagIdNotFoundException e) containsPerson(personId1) &&
      @                                    containsPerson(personId2) &&
      @                                    personId1!=personId2      &&
      @                                    getPerson(personId2).isLinked(getPerson(personId1)) &&
      @                                    !getPerson(personId2).containsTag(tagId);
      @ signals (EqualPersonIdException e) containsPerson(personId1) &&
      @                                    containsPerson(personId2) &&
      @                                    personId1!=personId2      &&
      @                                    getPerson(personId2).isLinked(getPerson(personId1)) &&
      @                                    getPerson(personId2).containsTag(tagId) &&
      @                                    getPerson(personId2).getTag(tagId).hasPerson(getPerson(personId1));
      @*/
    public /*@ safe @*/ void addPersonToTag(int personId1, int personId2, int tagId) throws PersonIdNotFoundException,
            RelationNotFoundException, TagIdNotFoundException, EqualPersonIdException;

    /*@ public normal_behavior
      @ requires containsPerson(personId) &&
      @          getPerson(personId).containsTag(tagId);
      @ ensures \result == getPerson(personId).getTag(tagId).getValueSum();
      @ also
      @ public exceptional_behavior
      @ signals (PersonIdNotFoundException e) !containsPerson(personId);
      @ signals (TagIdNotFoundException e) containsPerson(personId) &&
      @                                    !getPerson(personId).containsTag(tagId);
      @*/
    public /*@ pure @*/ int queryTagValueSum(int personId, int tagId) throws PersonIdNotFoundException, TagIdNotFoundException;

    /*@ public normal_behavior
      @ requires containsPerson(personId) &&
      @          getPerson(personId).containsTag(tagId);
      @ ensures \result == getPerson(personId).getTag(tagId).getAgeVar();
      @ also
      @ public exceptional_behavior
      @ signals (PersonIdNotFoundException e) !containsPerson(personId);
      @ signals (TagIdNotFoundException e) containsPerson(personId) &&
      @                                    !getPerson(personId).containsTag(tagId);
      @*/
    public /*@ pure @*/ int queryTagAgeVar(int personId, int tagId) throws PersonIdNotFoundException, TagIdNotFoundException;

    /*@ public normal_behavior
      @ requires containsPerson(personId1) &&
      @          containsPerson(personId2) &&
      @          getPerson(personId2).containsTag(tagId) &&
      @          getPerson(personId2).getTag(tagId).hasPerson(getPerson(personId1));
      @ assignable getPerson(personId2).getTag(tagId).persons;
      @ ensures !getPerson(personId2).getTag(tagId).hasPerson(getPerson(personId1));
      @ also
      @ public exceptional_behavior
      @ signals (PersonIdNotFoundException e) !containsPerson(personId1);
      @ signals (PersonIdNotFoundException e) containsPerson(personId1) &&
      @                                        !containsPerson(personId2);
      @ signals (TagIdNotFoundException e) containsPerson(personId1) &&
      @                                    containsPerson(personId2) &&
      @                                    !getPerson(personId2).containsTag(tagId);
      @ signals (PersonIdNotFoundException e) containsPerson(personId1) &&
      @                                     containsPerson(personId2) &&
      @                                     getPerson(personId2).containsTag(tagId) &&
      @                                     !getPerson(personId2).getTag(tagId).hasPerson(getPerson(personId1));
      @*/
    public /*@ safe @*/ void delPersonFromTag(int personId1, int personId2, int tagId) throws PersonIdNotFoundException,
            TagIdNotFoundException;

    /*@ public normal_behavior
      @ requires containsPerson(personId) &&
      @          getPerson(personId).containsTag(tagId);
      @ assignable getPerson(personId).tags;
      @ ensures !getPerson(personId).containsTag(tagId);
      @ also
      @ public exceptional_behavior
      @ signals (PersonIdNotFoundException e) !containsPerson(personId);
      @ signals (TagIdNotFoundException e) containsPerson(personId) &&
      @                                    !getPerson(personId).containsTag(tagId);
     */
    public /*@ safe @*/ void delTag(int personId, int tagId) throws PersonIdNotFoundException,
            TagIdNotFoundException;

    //@ ensures \result == (\exists int i; 0 <= i && i < messages.length; messages[i].getId() == id);
    public /*@ pure @*/ boolean containsMessage(int id);


    /*@ public normal_behavior
      @ requires !containsMessage(message.getId()) &&
      @           (message instanceof EmojiMessageInterface) ==> containsEmojiId(((EmojiMessageInterface) message).getEmojiId()) &&
      @            (message.getType() == 0) ==> !message.getPerson1().equals(message.getPerson2()) &&
      @             (message instanceof ForwardMessageInterface) ==> message.getPerson1().getReceivedArticles.contains(((ForwardMessageInterface) message).getArticleId);
      @ assignable messages;
      @ ensures containsMessage(message.getId());
      @ also
      @ public exceptional_behavior
      @ signals (EqualMessageIdException e) containsMessage(message.getId());
      @ signals (EmojiIdNotFoundException e) !containsMessage(message.getId()) &&
      @                                       (message instanceof EmojiMessageInterface) &&
      @                                       !containsEmojiId(((EmojiMessageInterface) message).getEmojiId());
      @ signals (ArticleIdNotFoundException e) !containsMessage(message.getId()) &&
      @                                       (message instanceof ForwardMessageInterface) &&
      @                                       !containsArticle(((ForwardMessageInterface) message).getArticleId());
      @ signals (ArticleIdNotFoundException e) !containsMessage(message.getId()) &&
      @                                       (message instanceof ForwardMessageInterface) &&
      @                                       containsArticle(((ForwardMessageInterface) message).getArticleId()) &&
      @                                       !(message.getPerson1().getReceivedArticles().contains(((ForwardMessageInterface) message).getArticleId()));
      @ signals (EqualPersonIdException e) !containsMessage(message.getId()) &&
      @                                     ((message instanceof EmojiMessageInterface) ==>
      @                                     containsEmojiId(((EmojiMessageInterface) message).getEmojiId())) &&
      @                                     ((message instanceof ForwardMessageInterface) ==>
      @                                     containsArticle(((ForwardMessageInterface) message).getArticleId()) &&
      @                                     (message.getPerson1().getReceivedArticles().contains(((ForwardMessageInterface) message).getArticleId()))) &&
      @                                     message.getType() == 0 &&
      @                                     message.getPerson1().equals(message.getPerson2());
      @*/
    public /*@ safe @*/ void addMessage(MessageInterface message) throws
            EqualMessageIdException, EmojiIdNotFoundException, EqualPersonIdException, ArticleIdNotFoundException;

    /*@ public normal_behavior
      @ requires containsMessage(id);
      @ ensures (\exists int i; 0 <= i && i < messages.length; messages[i].getId() == id &&
      @         \result == messages[i]);
      @ public normal_behavior
      @ requires !containsMessage(id);
      @ ensures \result == null;
      @*/
    public /*@ pure @*/ MessageInterface getMessage(int id);

    /*@ public normal_behavior
      @ requires containsMessage(id) && getMessage(id).getType() == 0 &&
      @          getMessage(id).getPerson1().isLinked(getMessage(id).getPerson2()) &&
      @          getMessage(id).getPerson1() != getMessage(id).getPerson2();
      @ assignable messages, emojiHeatList[*];
      @ assignable getMessage(id).getPerson1().socialValue, getMessage(id).getPerson1().money;
      @ assignable getMessage(id).getPerson2().messages,
      @            getMessage(id).getPerson2().socialValue,
      @            getMessage(id).getPerson2().money,
      @            getMessage(id).getPerson2().receivedArticles;
      @ ensures !containsMessage(id);
      @ ensures \old(getMessage(id)).getPerson1().getSocialValue() ==
      @         \old(getMessage(id).getPerson1().getSocialValue()) + \old(getMessage(id)).getSocialValue() &&
      @         \old(getMessage(id)).getPerson2().getSocialValue() ==
      @         \old(getMessage(id).getPerson2().getSocialValue()) + \old(getMessage(id)).getSocialValue();
      @ ensures (\old(getMessage(id)) instanceof RedEnvelopeMessageInterface) ==>
      @         (\old(getMessage(id)).getPerson1().getMoney() ==
      @         \old(getMessage(id).getPerson1().getMoney()) - ((RedEnvelopeMessageInterface)\old(getMessage(id))).getMoney() &&
      @         \old(getMessage(id)).getPerson2().getMoney() ==
      @         \old(getMessage(id).getPerson2().getMoney()) + ((RedEnvelopeMessageInterface)\old(getMessage(id))).getMoney());
      @ ensures (\old(getMessage(id)) instanceof ForwardMessageInterface) ==>
      @         ((\old(getMessage(id)).getPerson2().getReceivedArticles().get(0).equals(((ForwardMessageInterface)\old(getMessage(id))).getArticleId())) &&
      @         (\forall int i; 0 <= i && i < \old(getMessage(id).getPerson2().getReceivedArticles().size());
      @                                       \old(getMessage(id)).getPerson2().getReceivedArticles().get(i+1) == \old(getMessage(id).getPerson2().getReceivedArticles().get(i))) &&
      @         \old(getMessage(id)).getPerson2().getReceivedArticles().size() == \old(getMessage(id).getPerson2().getReceivedArticles().size()) + 1);
      @ ensures (!(\old(getMessage(id)) instanceof RedEnvelopeMessageInterface)) ==> (\not_assigned(persons[*].money));
      @ ensures (\old(getMessage(id)) instanceof EmojiMessageInterface) ==>
      @         (\exists int i; 0 <= i && i < emojiIdList.length && emojiIdList[i] == ((EmojiMessageInterface)\old(getMessage(id))).getEmojiId();
      @         emojiHeatList[i] == \old(emojiHeatList[i]) + 1);
      @ ensures (!(\old(getMessage(id)) instanceof EmojiMessageInterface)) ==> \not_assigned(emojiHeatList);
      @ ensures (\forall int i; 0 <= i && i < \old(getMessage(id).getPerson2().getMessages().size());
      @          \old(getMessage(id)).getPerson2().getMessages().get(i+1) == \old(getMessage(id).getPerson2().getMessages().get(i)));
      @ ensures \old(getMessage(id)).getPerson2().getMessages().get(0).equals(\old(getMessage(id)));
      @ ensures \old(getMessage(id)).getPerson2().getMessages().size() == \old(getMessage(id).getPerson2().getMessages().size()) + 1;
      @ also
      @ public normal_behavior
      @ requires containsMessage(id) && getMessage(id).getType() == 1 &&
      @           getMessage(id).getPerson1().containsTag(getMessage(id).getTag().getId());
      @ assignable messages, emojiHeatList[*];
      @ assignable getMessage(id).getPerson1().socialValue, getMessage(id).getPerson1().money;
      @ assignable getMessage(id).getTag().persons[*].messages,
      @            getMessage(id).getTag().persons[*].socialValue,
      @            getMessage(id).getTag().persons[*].money,
      @            getMessage(id).getTag().persons[*].receivedArticles;
      @ ensures !containsMessage(id)
      @ ensures \old(getMessage(id)).getPerson1().getSocialValue() ==
      @         \old(getMessage(id).getPerson1().getSocialValue())+ \old(getMessage(id)).getSocialValue();
      @ ensures (\forall PersonInterface p; \old(getMessage(id)).getTag().hasPerson(p); p.getSocialValue() ==
      @         \old(p.getSocialValue()) + \old(getMessage(id)).getSocialValue());
      @ ensures (\old(getMessage(id)) instanceof RedEnvelopeMessageInterface) && (\old(getMessage(id)).getTag().getSize() > 0) ==>
      @          (\exists int i; i == ((RedEnvelopeMessageInterface)\old(getMessage(id))).getMoney()/\old(getMessage(id)).getTag().getSize();
      @           \old(getMessage(id)).getPerson1().getMoney() ==
      @           \old(getMessage(id).getPerson1().getMoney()) - i*\old(getMessage(id)).getTag().getSize() &&
      @           (\forall PersonInterface p; \old(getMessage(id)).getTag().hasPerson(p);
      @           p.getMoney() == \old(p.getMoney()) + i));
      @ ensures (\old(getMessage(id)) instanceof ForwardMessageInterface) && (\old(getMessage(id)).getTag().getSize() > 0) ==>
      @         (\forall PersonInterface p; \old(getMessage(id)).getTag().hasPerson(p); p.getReceivedArticles().get(0).equals(((ForwardMessageInterface)\old(getMessage(id))).getArticleId())) &&
      @         (\forall PersonInterface p; \old(getMessage(id)).getTag().hasPerson(p); (\forall int i; 0 <= i && i < \old(p.getReceivedArticles().size());
      @                                                                         p.getReceivedArticles().get(i+1) == \old(p.getReceivedArticles().get(i)))) &&
      @         (\forall PersonInterface p; \old(getMessage(id)).getTag().hasPerson(p); p.getReceivedArticles().size() == \old(p.getReceivedArticles().size()) + 1);
      @ ensures (\old(getMessage(id)) instanceof EmojiMessageInterface) ==>
      @         (\exists int i; 0 <= i && i < emojiIdList.length && emojiIdList[i] == ((EmojiMessageInterface)\old(getMessage(id))).getEmojiId();
      @          emojiHeatList[i] == \old(emojiHeatList[i]) + 1);
      @ ensures (\forall PersonInterface p; \old(getMessage(id)).getTag().hasPerson(p); p.getMessages().get(0).equals(\old(getMessage(id))));
      @ ensures (\forall PersonInterface p; \old(getMessage(id)).getTag().hasPerson(p); (\forall int i; 0 <= i && i < \old(p.getMessages().size());
      @                                                                         p.getMessages().get(i+1) == \old(p.getMessages().get(i))));
      @ ensures (\forall PersonInterface p; \old(getMessage(id)).getTag().hasPerson(p); p.getMessages().size() == \old(p.getMessages().size()) + 1);
      @ also
      @ public exceptional_behavior
      @ signals (MessageIdNotFoundException e) !containsMessage(id);
      @ signals (RelationNotFoundException e) containsMessage(id) && getMessage(id).getType() == 0 &&
      @          !(getMessage(id).getPerson1().isLinked(getMessage(id).getPerson2()));
      @ signals (TagIdNotFoundException e) containsMessage(id) && getMessage(id).getType() == 1 &&
      @          !getMessage(id).getPerson1().containsTag(getMessage(id).getTag().getId());
      @*/
    public /*@ safe @*/ void sendMessage(int id) throws
            RelationNotFoundException, MessageIdNotFoundException, TagIdNotFoundException;

    /*@ public normal_behavior
      @ requires containsPerson(id);
      @ ensures \result == getPerson(id).getSocialValue();
      @ also
      @ public exceptional_behavior
      @ signals (PersonIdNotFoundException e) !containsPerson(id);
      @*/
    public /*@ pure @*/ int querySocialValue(int id) throws PersonIdNotFoundException;

    /*@ public normal_behavior
      @ requires containsPerson(id);
      @ ensures \result == getPerson(id).getReceivedMessages();
      @ also
      @ public exceptional_behavior
      @ signals (PersonIdNotFoundException e) !containsPerson(id);
      @*/
    public /*@ pure @*/ List<MessageInterface> queryReceivedMessages(int id) throws PersonIdNotFoundException;

    //@ ensures \result == (\exists int i; 0 <= i && i < emojiIdList.length; emojiIdList[i] == id);
    public /*@ pure @*/ boolean containsEmojiId(int id);

    /*@ public normal_behavior
      @ requires !containsEmojiId(id);
      @ assignable emojiIdList, emojiHeatList;
      @ ensures (\exists int i; 0 <= i && i < emojiIdList.length; emojiIdList[i] == id && emojiHeatList[i] == 0);
      @ ensures emojiIdList.length == \old(emojiIdList.length) + 1 &&
      @          emojiHeatList.length == \old(emojiHeatList.length) + 1;
      @ ensures (\forall int i; 0 <= i && i < \old(emojiIdList.length);
      @          (\exists int j; 0 <= j && j < emojiIdList.length; emojiIdList[j] == \old(emojiIdList[i]) &&
      @          emojiHeatList[j] == \old(emojiHeatList[i])));
      @ also
      @ public exceptional_behavior
      @ signals (EqualEmojiIdException e) containsEmojiId(id);
      @*/
    public void storeEmojiId(int id) throws EqualEmojiIdException;

    /*@ public normal_behavior
      @ requires containsPerson(id);
      @ ensures \result == getPerson(id).getMoney();
      @ also
      @ public exceptional_behavior
      @ signals (PersonIdNotFoundException e) !containsPerson(id);
      @*/
    public /*@ pure @*/ int queryMoney(int id) throws PersonIdNotFoundException;

    /*@ public normal_behavior
      @ requires containsEmojiId(id);
      @ ensures (\exists int i; 0 <= i && i < emojiIdList.length; emojiIdList[i] == id &&
      @          \result == emojiHeatList[i]);
      @ also
      @ public exceptional_behavior
      @ requires !containsEmojiId(id);
      @ signals_only EmojiIdNotFoundException;
      @*/
    public /*@ pure @*/ int queryPopularity(int id) throws EmojiIdNotFoundException;

    /*@ public normal_behavior
      @ assignable emojiIdList, emojiHeatList, messages;
      @ ensures (\forall int i; 0 <= i && i < \old(emojiIdList.length);
      @          (\old(emojiHeatList[i] >= limit) ==>
      @          (\exists int j; 0 <= j && j < emojiIdList.length; emojiIdList[j] == \old(emojiIdList[i]))));
      @ ensures (\forall int i; 0 <= i && i < emojiIdList.length;
      @          (\exists int j; 0 <= j && j < \old(emojiIdList.length);
      @          emojiIdList[i] == \old(emojiIdList[j]) && emojiHeatList[i] == \old(emojiHeatList[j])));
      @ ensures emojiIdList.length ==
      @          (\num_of int i; 0 <= i && i < \old(emojiIdList.length); \old(emojiHeatList[i] >= limit));
      @ ensures emojiIdList.length == emojiHeatList.length;
      @ ensures (\forall int i; 0 <= i && i < \old(messages.length);
      @          (\old(messages[i]) instanceof EmojiMessageInterface &&
      @           containsEmojiId(\old(((EmojiMessageInterface)messages[i]).getEmojiId()))  ==> \not_assigned(\old(messages[i])) &&
      @           (\exists int j; 0 <= j && j < messages.length; messages[j].equals(\old(messages[i])))));
      @ ensures (\forall int i; 0 <= i && i < \old(messages.length);
      @          (!(\old(messages[i]) instanceof EmojiMessageInterface) ==> \not_assigned(\old(messages[i])) &&
      @           (\exists int j; 0 <= j && j < messages.length; messages[j].equals(\old(messages[i])))));
      @ ensures messages.length == (\num_of int i; 0 <= i && i < \old(messages.length);
      @          (\old(messages[i]) instanceof EmojiMessageInterface) ==>
      @           (containsEmojiId(\old(((EmojiMessageInterface)messages[i]).getEmojiId()))));
      @ ensures \result == emojiIdList.length;
      @*/
    public int deleteColdEmoji(int limit);

    /*@ public normal_behavior
      @ requires containsPerson(id) && getPerson(id).acquaintance.length != 0;
      @ ensures \result == (\min int bestId;
      @         (\exists int i; 0 <= i && i < getPerson(id).acquaintance.length &&
      @             getPerson(id).acquaintance[i].getId() == bestId;
      @             (\forall int j; 0 <= j && j < getPerson(id).acquaintance.length;
      @                 getPerson(id).value[j] <= getPerson(id).value[i]));
      @         bestId);
      @ public exceptional_behavior
      @ signals (PersonIdNotFoundException e) !containsPerson(id);
      @ signals (AcquaintanceNotFoundException e) containsPerson(id) &&
      @         getPerson(id).acquaintance.length == 0;
      @*/
    public /*@ pure @*/ int queryBestAcquaintance(int id) throws
            PersonIdNotFoundException, AcquaintanceNotFoundException;


    /*@ ensures \result ==
      @         (\sum int i, j; 0 <= i && i < j && j < persons.length
      @                         && persons[i].acquaintance.length > 0 && queryBestAcquaintance(persons[i].getId()) == persons[j].getId()
      @                         && persons[j].acquaintance.length > 0 && queryBestAcquaintance(persons[j].getId()) == persons[i].getId();
      @                         1);
      @*/
    public /*@ pure @*/ int queryCoupleSum();


    /*@ public normal_behavior
      @ requires containsPerson(id1) && id1 == id2 ;
      @ ensures \result==0 ;
      @ also
      @ public normal_behavior
      @ requires containsPerson(id1) &&
      @          containsPerson(id2) &&
      @          id1 != id2 &&
      @          (\exists PersonInterface[] path;
      @          path.length >= 2 &&
      @          path[0].equals(getPerson(id1)) &&
      @          path[path.length - 1].equals(getPerson(id2));
      @          (\forall int i; 1 <= i && i < path.length; path[i - 1].isLinked(path[i])));
      @ ensures  (\exists PersonInterface[] pathM;
      @          pathM.length >= 2 &&
      @          pathM[0].equals(getPerson(id1)) &&
      @          pathM[pathM.length - 1].equals(getPerson(id2)) &&
      @          (\forall int i; 1 <= i && i < pathM.length; pathM[i - 1].isLinked(pathM[i]));
      @          (\forall PersonInterface[] path;
      @          path.length >= 2 &&
      @          path[0].equals(getPerson(id1)) &&
      @          path[path.length - 1].equals(getPerson(id2)) &&
      @          (\forall int i; 1 <= i && i < path.length; path[i - 1].isLinked(path[i]));
      @          (\sum int i; 0 <= i && i < path.length; 1) >=
      @          (\sum int i; 0 <= i && i < pathM.length; 1)) &&
      @          \result==(\sum int i; 1 <= i && i < pathM.length; 1));
      @ also
      @ public exceptional_behavior
      @ signals (PersonIdNotFoundException e) !containsPerson(id1);
      @ signals (PersonIdNotFoundException e) containsPerson(id1) &&
      @                                       !containsPerson(id2);
      @ signals (PathNotFoundException e) containsPerson(id1) &&
      @                                   containsPerson(id2) &&
      @         !(\exists PersonInterface[] path;
      @         path.length >= 2 &&
      @         path[0].equals(getPerson(id1)) &&
      @         path[path.length - 1].equals(getPerson(id2));
      @         (\forall int i; 1 <= i && i < path.length; path[i - 1].isLinked(path[i])));
      @*/
    public /*@ pure @*/ int queryShortestPath(int id1,int id2) throws PersonIdNotFoundException, PathNotFoundException;

    //@ ensures \result == (\exists int i; 0 <= i && i < accounts.length; accounts[i].id == id);
    public /*@ pure @*/ boolean containsAccount(int id);

    /*@ public normal_behavior
     @ requires containsPerson(personId) &&
     @          !containsAccount(accountId);
     @ assignable accounts;
     @ ensures containsAccount(accountId) && accounts[accountId].containsFollower(personId) && accounts[accountId].getOwnerId() == personId;
     @ ensures (\exists int i; 0 <= i && i < accounts[accountId].followers.length; accounts[accountId].followers[i].getId() == personId && accounts[accountId].contributions[i] == 0);
     @ also
     @ public exceptional_behavior
     @ signals (PersonIdNotFoundException e) !containsPerson(personId);
     @ signals (EqualOfficialAccountIdException e) containsPerson(personId) &&
     @                                     containsAccount(accountId);
     @*/
    public /*@ safe @*/ void createOfficialAccount(int personId, int accountId, String name) throws PersonIdNotFoundException, EqualOfficialAccountIdException;

    /*@ public normal_behavior
      @ requires containsPerson(personId) &&
      @          containsAccount(accountId) &&
      @          accounts[accountId].ownerId == personId;
      @ assignable accounts;
      @ ensures !containsAccount(accountId);
      @ also
      @ public exceptional_behavior
      @ signals (PersonIdNotFoundException e) !containsPerson(personId);
      @ signals (OfficialAccountIdNotFoundException e) containsPerson(personId) &&
      @                                        !containsAccount(accountId);
      @ signals (DeleteOfficialAccountPermissionDeniedException e) containsPerson(personId) &&
      @                                           containsAccount(accountId) &&
      @                                           accounts[accountId].ownerId != personId;
     */
    public /*@ safe @*/ void deleteOfficialAccount(int personId, int accountId) throws PersonIdNotFoundException, OfficialAccountIdNotFoundException, DeleteOfficialAccountPermissionDeniedException;

    //@ ensures \result == (\exists int i; 0 <= i && i < articles.length; articles[i] == id);
    public /*@ pure @*/ boolean containsArticle(int id);

    /*@ public normal_behavior
      @ requires containsPerson(personId) &&
      @          containsAccount(accountId) &&
      @          !containsArticle(articleId) &&
      @          accounts[accountId].containsFollower(getPerson(personId));
      @ assignable articles, articleContributors, accounts[accountId].articles, accounts[accountId].contributions, accounts[accountId].followers[*].receivedArticles;
      @ ensures containsArticle(articleId) && accounts[accountId].containsArticle(articleId);
      @ ensures (\exists int i; 0 <= i && i < accounts[accountId].followers.length;
      @                                       accounts[accountId].followers[i].getId() == personId &&
      @                                       accounts[accountId].contributions[i] == \old(accounts[accountId].contributions[i]) + 1);
      @ ensures (\exists int i; 0 <= i && i < articles.length; articles[i] == articleId && articleContributors[i] == personId);
      @ ensures (\forall PersonInterface p; accounts[accountId].containsFollower(p); p.getReceivedArticles().get(0).equals(articleId));
      @ ensures (\forall PersonInterface p; accounts[accountId].containsFollower(p); (\forall int i; 0 <= i && i < \old(p.getReceivedArticles().size());
      @                                                                         p.getReceivedArticles().get(i+1) == \old(p.getReceivedArticles().get(i))));
      @ ensures (\forall PersonInterface p; accounts[accountId].containsFollower(p); p.getReceivedArticles().size() == \old(p.getReceivedArticles().size() + 1));
      @ also
      @ public exceptional_behavior
      @ signals (PersonIdNotFoundException e) !containsPerson(personId);
      @ signals (OfficialAccountIdNotFoundException e) containsPerson(personId) &&
      @                                        !containsAccount(accountId);
      @ signals (EqualArticleIdException e) containsPerson(personId) &&
      @                                     containsAccount(accountId) &&
      @                                     containsArticle(articleId);
      @ signals (ContributePermissionDeniedException e) containsPerson(personId) &&
      @                                        containsAccount(accountId) &&
      @                                        !containsArticle(articleId) &&
      @                                        !accounts[accountId].containsFollower(getPerson(personId));
      @*/
    public /*@ safe @*/ void contributeArticle(int personId,int accountId,int articleId) throws PersonIdNotFoundException, OfficialAccountIdNotFoundException, EqualArticleIdException, ContributePermissionDeniedException;

    /*@ public normal_behavior
      @ requires containsPerson(personId) &&
      @          containsAccount(accountId) &&
      @          accounts[accountId].containsArticle(articleId) &&
      @          accounts[accountId].ownerId == personId;
      @ assignable accounts[accountId].articles, accounts[accountId].contributions, accounts[accountId].followers[*].receivedArticles;
      @ ensures !accounts[accountId].containsArticle(articleId);
      @ ensures (\forall PersonInterface p; accounts[accountId].containsFollower(p); (\forall int i; 0 <= i && i < (p.getReceivedArticles().size());
      @                                                                         p.getReceivedArticles().get(i) != articleId));
      @ ensures (\exists int i; 0 <= i < articles.length;
      @                                     articles[i] == articleId &&
      @                                     (\exists int j; 0 <= j && j < accounts[accountId].followers.length;
      @                                                                   accounts[accountId].followers[j].getId() == articleContributors[i] &&
      @                                                                   accounts[accountId].contributions[j] == \old(accounts[accountId].contributions[j]) - 1));
      @ ensures (\forall PersonInterface p; accounts[accountId].containsFollower(p);
      @          (\forall int i; 0 <= i && i < (p.getReceivedArticles().size());
      @           (\forall int j; i < j && j < (p.getReceivedArticles().size());
      @                   \old(p.getReceivedArticles()).indexOf(
      @                   p.getReceivedArticles().get(i)) <
      @                   \old(p.getReceivedArticles()).indexOf(
      @                   p.getReceivedArticles().get(j)))));
      @ also
      @ public exceptional_behavior
      @ signals (PersonIdNotFoundException e) !containsPerson(personId);
      @ signals (OfficialAccountIdNotFoundException e) containsPerson(personId) &&
      @                                        !containsAccount(accountId);
      @ signals (ArticleIdNotFoundException e) containsPerson(personId) &&
      @                                     containsAccount(accountId) &&
      @                                     !accounts[accountId].containsArticle(articleId);
      @ signals (DeleteArticlePermissionDeniedException e) containsPerson(personId) &&
      @                                        containsAccount(accountId) &&
      @                                        accounts[accountId].containsArticle(articleId) &&
      @                                        accounts[accountId].ownerId != personId;
      @*/
    public /*@ safe @*/ void deleteArticle(int personId,int accountId,int articleId) throws PersonIdNotFoundException, OfficialAccountIdNotFoundException, ArticleIdNotFoundException, DeleteArticlePermissionDeniedException;

    /*@ public normal_behavior
      @ requires containsPerson(personId) &&
      @          containsAccount(accountId) &&
      @          !accounts[accountId].containsFollower(getPerson(personId));
      @ assignable accounts[accountId].followers, accounts[accountId].contributions;
      @ ensures accounts[accountId].containsFollower(getPerson(personId));
      @ ensures (\exists int i; 0 <= i && i < accounts[accountId].followers.length;
      @                                       accounts[accountId].followers[i].getId() == personId && accounts[accountId].contributions[i] == 0);
      @ also
      @ public exceptional_behavior
      @ signals (PersonIdNotFoundException e) !containsPerson(personId);
      @ signals (OfficialAccountIdNotFoundException e) containsPerson(personId) &&
      @                                        !containsAccount(accountId);
      @ signals (EqualPersonIdException e) containsPerson(personId) &&
      @                                     containsAccount(accountId) &&
      @                                     accounts[accountId].containsFollower(getPerson(personId));
      @*/
    public /*@ safe @*/ void followOfficialAccount(int personId,int accountId) throws PersonIdNotFoundException, OfficialAccountIdNotFoundException, EqualPersonIdException;

    /*@ public normal_behavior
      @ requires containsAccount(id);
      @ ensures \result == accounts[accountId].getBestContributor();
      @ also
      @ public exceptional_behavior
      @ signals (OfficialAccountIdNotFoundException e) !containsAccount(id);
      @*/
    public /*@ pure @*/ int queryBestContributor(int id) throws OfficialAccountIdNotFoundException;

    /*@ public normal_behavior
      @ requires containsPerson(id);
      @ ensures \result == getPerson(id).queryReceivedArticles();
      @ also
      @ public exceptional_behavior
      @ signals (PersonIdNotFoundException e) !containsPerson(id);
      @*/
    public /*@ pure @*/ List<Integer> queryReceivedArticles(int id) throws PersonIdNotFoundException;
}
