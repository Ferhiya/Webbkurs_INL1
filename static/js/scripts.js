
    // JavaScript function to toggle transaction visibility
    function toggleTransactions(accountId) {
        var transactionRow = document.getElementById('transactions-' + accountId);
        if (transactionRow.style.display === 'none') {
            transactionRow.style.display = 'table-row';  // Show the transactions
        } else {
            transactionRow.style.display = 'none';  // Hide the transactions
        }
    }



//search filter country in start page
function filterCountries() {
    var input = document.getElementById("countrySearch");
    var filter = input.value.toLowerCase();
    var table = document.getElementById("countryTable");
    var tr = table.getElementsByTagName("tr");

    for (var i = 0; i < tr.length; i++) {
        var td = tr[i].getElementsByTagName("td")[0]; // Search in the first column (Country)
        if (td) {
            var txtValue = td.textContent || td.innerText;
            if (txtValue.toLowerCase().indexOf(filter) > -1) {
                tr[i].style.display = "";
            } else {
                tr[i].style.display = "none";
            }
        }
    }
}