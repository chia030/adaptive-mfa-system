<script>
import Login from './Login.svelte';
	import MFASelection from './MFASelection.svelte';
	
	let authenticated = false;
	let mfaRequired = false;
	let mfaPassed = false;
	let availableMFAMethods = [];
	
	// Simulate a login process
	function handleLogin(event) {
	  // Here you’d call your backend API
	  authenticated = true;
	  mfaRequired = true;
	  availableMFAMethods = [
		{ id: 'sms', name: 'SMS OTP' },
		{ id: 'email', name: 'Email OTP' }
	  ];
	}
	
	// Simulate an MFA selection handling
	function handleSelectMethod(event) {
	  // For demo purposes, assume MFA is successfully completed
	  mfaPassed = true;
	}
</script>

<main>
	{#if !authenticated}
	<Login on:login={handleLogin}/>
	{:else if mfaRequired && !mfaPassed}
		<MFASelection methods={availableMFAMethods} on:select={handleSelectMethod}/>
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
