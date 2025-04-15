<script>
	import Login from './Login.svelte';
	import MFASelection from './MFASelection.svelte';
	import OTPVerification from './OTPVerification.svelte';

	//TODO: add logout
	//TODO: fix - very messy ew
	
	let isAuthenticated = false;
	let isMfaRequired = false;
	let isMfaPassed = false;
	let thisAvailableMFAMethods = [];
	
	let token = "";
  	let userEmail = "";
	let fingerprint = "";
	
	// login process
	function handleLogin(event) {
		event.preventDefault();
		const { username, password, device_id, authenticated, mfaRequired, mfaPassed, availableMFAMethods, token } = event.detail;
		userEmail = username;
		fingerprint = device_id;
		isAuthenticated = authenticated;
		isMfaRequired = mfaRequired;
		isMfaPassed = mfaPassed;
		thisAvailableMFAMethods = availableMFAMethods || [ { id: 'sms', name: 'SMS OTP' }, { id: 'email', name: 'Email OTP' } ];

	}
	
	// Simulate an MFA selection handling
	function handleSelectMethod(event) {
		// log choice but only email is available in backend so that will be it
		console.log("MFA method selected:", event.detail);
	  // For demo purposes, assume MFA is successfully completed
	//   isMfaPassed = true;
	}

	async function handleMfaVerification({detail: otp}) {
		try {
			const response = await fetch('http://localhost:8000/mfa/verify-otp', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					email: userEmail,
					otp: otp,
					device_id: fingerprint
				})
			});
			const data = await response.json();
			if (response.ok) {
				isMfaPassed = true;
				token = data.access_token;
			} else {
				console.error('OTP verification failed:', data.detail);
			}
		} catch (error) {
			console.error('Error during OTP verification:', error);
		}
	}
</script>

<main>
	{#if !isAuthenticated}
	<Login on:login={(event) => handleLogin(event)}/>
	{:else if isMfaRequired && !isMfaPassed}
		<!-- MFASelection for choosing a method -->
		<MFASelection methods={thisAvailableMFAMethods} on:select={handleSelectMethod}/>
		<!-- OTPVerification for entering the received OTP -->
		<OTPVerification on:verify={handleMfaVerification} />
	{:else}
		<h2>Welcome, you are now securely authenticated!</h2>
		<!-- Optionally display or store the received token -->
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
