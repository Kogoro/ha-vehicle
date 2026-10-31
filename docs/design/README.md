# Design notes

Mockups made before building the three cards (rendered with Home Assistant's own components and theme).

| Image | |
|-------|-|
| [info-card-layouts.png](info-card-layouts.png) | Info card: normal, compact and minimal layout |
| [activity-card.png](activity-card.png) | Activity card: filter chips only for types that exist; editor toggles |
| [entry-card.png](entry-card.png) | Entry card: tabs follow the drive type; editor toggles |
| [phone-layout.png](phone-layout.png) | Suggested phone order: info, add entry, activity |

Decisions:

- The info card is read-only and has no "needs attention" label. Notifications are an automation (see the blueprint in the README).
- Statistics are one consumption row and one costs-this-month row (fuel/charging and service). The price of the last refuel is not shown.
- Receipts and invoices are linked in the activity card and uploaded only in the entry card.
- A type (refuels, charges, service) only appears when it applies and, in the activity card, when there are entries of that type; each type can also be switched off.
