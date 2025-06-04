import com.oocourse.spec3.main.MessageInterface;
import com.oocourse.spec3.main.PersonInterface;
import com.oocourse.spec3.main.TagInterface;

public class Message implements MessageInterface {
    private int id;
    private int socialValue;
    private int type;
    private PersonInterface person1;
    private PersonInterface person2;
    private TagInterface tag;

    /*@ ensures type == 0;
   @ ensures tag == null;
   @ ensures id == messageId;
   @ ensures socialValue == messageSocialValue;
   @ ensures person1 == messagePerson1;
   @ ensures person2 == messagePerson2;
   @*/
    public Message(int messageId, int messageSocialValue,
        PersonInterface messagePerson1, PersonInterface messagePerson2) {
        this.id = messageId;
        this.socialValue = messageSocialValue;
        this.type = 0;
        this.person1 = messagePerson1;
        this.person2 = messagePerson2;
        this.tag = null;
    }

    /*@ ensures type == 1;
      @ ensures person2 == null;
      @ ensures id == messageId;
      @ ensures socialValue == messageSocialValue;
      @ ensures person1 == messagePerson1;
      @ ensures tag == messageTag;
      @*/
    public Message(int messageId, int messageSocialValue,
        PersonInterface messagePerson1, TagInterface messageTag) {
        this.id = messageId;
        this.socialValue = messageSocialValue;
        this.type = 1;
        this.person1 = messagePerson1;
        this.person2 = null;
        this.tag = messageTag;
    }

    public int getType() {
        return type;
    }

    public int getId() {
        return id;
    }

    public int getSocialValue() {
        return socialValue;
    }

    public PersonInterface getPerson1() {
        return person1;
    }

    public PersonInterface getPerson2() {
        return person2;
    }

    public TagInterface getTag() {
        return tag;
    }

    public boolean equals(Object obj) {
        if (obj == null || !(obj instanceof MessageInterface)) {
            return false;
        }
        MessageInterface message = (MessageInterface) obj;
        return message.getId() == id;
    }
}
