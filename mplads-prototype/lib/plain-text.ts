// Plain-language wording for each scoring rule: [why flagged, what to check].
// The release data keeps the original technical text; it is used as a fallback.
export const RULE_TEXT: Record<string, [string, string]> = {
  pending_recommendation_45d_flag: [
    'Recommendation waiting more than 45 days',
    'Check when it was received and whether it was rejected.',
  ],
  sanction_delay_45d_flag: [
    'Sanctioned more than 45 days after recommendation',
    'The official clock starts on the receipt date, which is not in the data, so this is an estimate.',
  ],
  open_over_one_year_flag: [
    'Still open more than a year after sanction',
    'Check the contract due date and any approved extension.',
  ],
  no_payment_three_months_flag: [
    'No payment seen 3 months after sanction',
    'The payment report may be incomplete.',
  ],
  paid_over_sanction_flag: [
    'More paid than sanctioned',
    'Check for a revised sanction and the final accounts.',
  ],
  completion_over_sanction_flag: [
    'Final cost more than sanctioned',
    'Check the approved scope and any revised sanction.',
  ],
  repeat_payment_report_flag: [
    'Same payment appears more than once in the report',
    'Transaction IDs are needed to tell a real double payment from a repeated report line.',
  ],
  march_rush_flag: [
    'Most of the money paid in March (year-end)',
    'Year-end payments can be normal; check work progress at the time of payment.',
  ],
  high_cost_peer_flag: [
    'Costs much more than similar earlier works',
    'Quantities, unit rates and specifications are not in the data; a bigger work can cost more.',
  ],
  high_similarity_review_flag: [
    'Description almost the same as another work',
    'Different locations or phases of a project can be legitimate.',
  ],
};
export const ruleText = (rule: string, reason: string, caution: string) =>
  RULE_TEXT[rule] ?? [reason, caution];
export const ruleName = (rule: string) =>
  RULE_TEXT[rule]?.[0] ?? rule.replace(/_flag$/, '').replaceAll('_', ' ');
