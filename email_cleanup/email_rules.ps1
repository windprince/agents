# Load the Outlook COM object
$Outlook = New-Object -ComObject Outlook.Application
$Namespace = $Outlook.GetNamespace("MAPI")
$Rules = $Namespace.DefaultStore.GetRules()

# Define an array to store issues
$RuleIssues = @()

# Check each rule
foreach ($Rule in $Rules) {
    $RuleIssue = @{
        Name          = $Rule.Name
        Enabled       = $Rule.Enabled
        ErrorMessage  = $null
    }

    # Check if the rule is enabled
    if (-not $Rule.Enabled) {
        $RuleIssue.ErrorMessage = "Rule is disabled"
    }

    # Check for missing folders
    foreach ($Action in $Rule.Actions) {
        if (($Action.ActionType -eq "olRuleActionMoveToFolder") -and ($Action.Folder = $null)) {
            $RuleIssue.ErrorMessage = "Missing folder in Move To Folder action"
        }
    }

    # Add rule with issues to the list
    if ($RuleIssue.ErrorMessage) {
        $RuleIssues += $RuleIssue
    }
}

# Export the issues to a CSV file
if ($RuleIssues.Count -gt 0) {
    $RuleIssues | Export-Csv -Path "C:\Users\psharmak\OneDrive\psharmak_agents\email_cleanup\RuleIssues.csv" -NoTypeInformation
    Write-Host "Analysis complete. Issues found and exported to OneDrive\psharmak_agents\email_cleanup\RuleIssues.csv on your desktop."
} else {
    Write-Host "No issues detected with the rules."
}
