<script>
import Login from './Login.svelte';
	import MFASelection from './MFASelection.svelte';
	
	let isAuthenticated = false;
	let isMfaRequired = false;
	let mfaPassed = false;
	let thisAvailableMFAMethods = [];
	
	// login process
	function handleLogin(event) {
		event.preventDefault();
		const { username, password, device_id, authenticated, mfaRequired, availableMFAMethods } = event.detail;
		isAuthenticated = authenticated;
		isMfaRequired = mfaRequired;
		thisAvailableMFAMethods = availableMFAMethods || [ { id: 'sms', name: 'SMS OTP' }, { id: 'email', name: 'Email OTP' } ];

	}
	
	// Simulate an MFA selection handling
	function handleSelectMethod(event) {
	  // For demo purposes, assume MFA is successfully completed
	  mfaPassed = true;
	}
</script>

<main>
	{#if !isAuthenticated}
	<Login on:login={(event) => handleLogin(event)}/>
	{:else if isMfaRequired && !mfaPassed}
		<MFASelection methods={thisAvailableMFAMethods} on:select={handleSelectMethod}/>
	{:else}
		<h2>Welcome, you are now securely authenticated!</h2>
	{/if} 
</main>

<style>
	main {
		text-align: center;
		padding: 1em;
		max-width: 240px;
		margin: 0 auto;
	}

	h1 {
		color: #ff3e00;
		text-transform: uppercase;
		font-size: 4em;
		font-weight: 100;
	}

	@media (min-width: 640px) {
		main {
			max-width: none;
		}
	}
</style>
