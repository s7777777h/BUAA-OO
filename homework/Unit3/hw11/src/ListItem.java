public class ListItem {
    private ListItem next;
    private ListItem prev;
    private Object value;

    public ListItem next() {
        return next;
    }

    public void setNext(ListItem next) {
        this.next = next;
    }

    public ListItem prev() {
        return prev;
    }

    public void setPrev(ListItem prev) {
        this.prev = prev;
    }

    public ListItem(Object value) {
        this.value = value;
    }

    public Object getValue() {
        return value;
    }

    public void setValue(Object value) {
        this.value = value;
    }

    public void remove() {
        if (prev != null) {
            prev.setNext(next);
        }
        if (next != null) {
            next.setPrev(prev);
        }
    }

    public void insertAfter(ListItem item) {
        item.setNext(next);
        item.setPrev(this);
        if (next != null) {
            next.setPrev(item);
        }
        setNext(item);
    }

    public void insertBefore(ListItem item) {
        item.setPrev(prev);
        item.setNext(this);
        if (prev != null) {
            prev.setNext(item);
        }
        setPrev(item);
    }
}
