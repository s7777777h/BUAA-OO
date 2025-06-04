import com.oocourse.spec3.main.PersonInterface;
import com.oocourse.spec3.main.RedEnvelopeMessageInterface;
import com.oocourse.spec3.main.TagInterface;

public class RedEnvelopeMessage extends Message implements RedEnvelopeMessageInterface {
    private int money;

    public boolean repOk() {
        return (getSocialValue() == money * 5);
    }

    /*@ ensures type == 0;
  @ ensures tag == null;
  @ ensures id == messageId;
  @ ensures person1 == messagePerson1;
  @ ensures person2 == messagePerson2;
  @ ensures money == luckyMoney;
  @*/
    public RedEnvelopeMessage(int messageId, int luckyMoney,
        PersonInterface messagePerson1, PersonInterface messagePerson2) {
        super(messageId, luckyMoney * 5, messagePerson1, messagePerson2);
        this.money = luckyMoney;
    }

    /*@ ensures type == 1;
      @ ensures person2 == null;
      @ ensures id == messageId;
      @ ensures person1 == messagePerson1;
      @ ensures tag == messageTag;
      @ ensures money == luckyMoney;
      @*/
    public RedEnvelopeMessage(int messageId, int luckyMoney,
        PersonInterface messagePerson1, TagInterface messageTag) {
        super(messageId, luckyMoney * 5, messagePerson1, messageTag);
        this.money = luckyMoney;
    }

    public int getMoney() {
        return money;
    }

}
