import com.oocourse.spec3.main.ForwardMessageInterface;
import com.oocourse.spec3.main.PersonInterface;
import com.oocourse.spec3.main.TagInterface;

public class ForwardMessage extends Message implements ForwardMessageInterface {
    private int articleId;

    /*@ ensures type == 0;
      @ ensures tag == null;
      @ ensures id == messageId;
      @ ensures person1 == messagePerson1;
      @ ensures person2 == messagePerson2;
      @ ensures articleId == article;
      @*/
    public ForwardMessage(int messageId, int article, PersonInterface messagePerson1,
        PersonInterface messagePerson2) {
        super(messageId, Math.abs(article) % 200,messagePerson1, messagePerson2);
        this.articleId = article;
    }

    /*@ ensures type == 1;
      @ ensures person2 == null;
      @ ensures id == messageId;
      @ ensures person1 == messagePerson1;
      @ ensures tag == messageTag;
      @ ensures articleId == article;
      @*/
    public ForwardMessage(int messageId, int article, PersonInterface messagePerson1,
        TagInterface messageTag) {
        super(messageId, Math.abs(article) % 200, messagePerson1, messageTag);
        this.articleId = article;
    }

    public boolean repOk() {
        return (getSocialValue() == Math.abs(articleId) % 200);
    }

    @Override
    public int getArticleId() {
        return articleId;
    }
}
