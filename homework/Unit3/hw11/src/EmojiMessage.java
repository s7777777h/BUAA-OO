import com.oocourse.spec3.main.EmojiMessageInterface;
import com.oocourse.spec3.main.PersonInterface;
import com.oocourse.spec3.main.TagInterface;

public class EmojiMessage extends Message implements EmojiMessageInterface {
    private int emojiId;

    /*@ ensures type == 0;
  @ ensures tag == null;
  @ ensures id == messageId;
  @ ensures person1 == messagePerson1;
  @ ensures person2 == messagePerson2;
  @ ensures emojiId == emojiNumber;
  @*/
    public EmojiMessage(int messageId, int emojiNumber, PersonInterface messagePerson1,
        PersonInterface messagePerson2) {
        super(messageId, emojiNumber, messagePerson1, messagePerson2);
        this.emojiId = emojiNumber;
    }

    /*@ ensures type == 1;
      @ ensures person2 == null;
      @ ensures id == messageId;
      @ ensures person1 == messagePerson1;
      @ ensures tag == messageTag;
      @ ensures emojiId == emojiNumber;
      @*/
    public EmojiMessage(int messageId, int emojiNumber,
        PersonInterface messagePerson1, TagInterface messageTag) {
        super(messageId, emojiNumber, messagePerson1, messageTag);
        this.emojiId = emojiNumber;
    }

    private boolean repOk() {
        return (getSocialValue() == emojiId);
    }

    public int getEmojiId() {
        return emojiId;
    }
}
