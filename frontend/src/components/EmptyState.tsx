export interface EmptyStateProps {
  reason?: "no-change" | "empty-watchlist";
}

export function EmptyState({ reason = "no-change" }: EmptyStateProps) {
  const messages = {
    "no-change": {
      title: "No meaningful change",
      subtitle: "Everything is tracking as expected.",
    },
    "empty-watchlist": {
      title: "Watchlist is empty",
      subtitle: "Add some symbols to get started.",
    },
  };

  const message = messages[reason];

  return (
    <section className="empty-state">
      <h2 className="empty-state__title">{message.title}</h2>
      <p className="empty-state__subtitle">{message.subtitle}</p>
    </section>
  );
}

