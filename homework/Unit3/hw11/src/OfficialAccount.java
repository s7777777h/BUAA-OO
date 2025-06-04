import com.oocourse.spec3.main.OfficialAccountInterface;
import com.oocourse.spec3.main.PersonInterface;

import java.util.HashMap;
import java.util.HashSet;

public class OfficialAccount implements OfficialAccountInterface {
    private final int ownerId;
    private final int id;
    private final String name;
    private final HashMap<Integer, PersonInterface> followers = new HashMap<>();
    private final HashSet<Integer> articles = new HashSet<>();
    private final HashMap<Integer, Integer> contributions = new HashMap<>();
    private final HashMap<Integer, Integer> articleContributors = new HashMap<>();

    public OfficialAccount(int ownerId, int id, String name) {
        this.ownerId = ownerId;
        this.id = id;
        this.name = name;
    }

    public int getOwnerId() {
        return ownerId;
    }

    public void addFollower(PersonInterface person) {
        if (!followers.containsKey(person.getId())) {
            followers.put(person.getId(), person);
            contributions.put(person.getId(), 0);
        }
    }

    public boolean containsFollower(PersonInterface person) {
        return followers.containsKey(person.getId());
    }

    public void addArticle(PersonInterface person, int id) {
        if (!articles.contains(id)) {
            articles.add(id);
            articleContributors.put(id, person.getId());
            if (followers.containsKey(person.getId())) {
                contributions.put(person.getId(), contributions.get(person.getId()) + 1);
            }
        }
    }

    public boolean containsArticle(int id) {
        return articles.contains(id);
    }

    public void removeArticle(int id) {
        if (articles.contains(id)) {
            articles.remove((Integer) id);
            articleContributors.remove((Integer) id);
        }
    }

    public int getBestContributor() {
        int bestId = -1;
        int maxContributions = -1;
        for (int id : contributions.keySet()) {
            if (contributions.get(id) > maxContributions ||
                (contributions.get(id) == maxContributions && id < bestId)) {
                maxContributions = contributions.get(id);
                bestId = id;
            }
        }
        return bestId;
    }

    public void subContribution(int articleId) {
        if (articles.contains(articleId)) {
            int contributorId = articleContributors.get(articleId);
            contributions.put(contributorId, contributions.get(contributorId) - 1);
        }
    }
}
